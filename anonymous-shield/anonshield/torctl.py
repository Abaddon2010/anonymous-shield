# Copyright (C) 2026 Abaddon2010
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later
# Licenca dupla: Apache-2.0 OU GPL-3.0-ou-posterior, a sua escolha. Ver LICENSE-APACHE e LICENSE na raiz.

"""Anonymous Shield — gerencia tor.exe + controle via stem (thread própria)."""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time

from PyQt6.QtCore import QObject, QThread, pyqtSignal

try:
    from stem.control import Controller
    from stem import Signal
    HAVE_STEM = True
except ImportError:  # pragma: no cover
    HAVE_STEM = False

from .config import AppConfig, app_dirs
from .i18n import t


def base_dir() -> str:
    """Pasta do projeto (ou bundle PyInstaller)."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def tor_bin() -> str:
    """Binário do Tor: no Linux prefere o tor do sistema; senão o embutido."""
    if os.name != "nt":
        import shutil as _sh
        for cand in (_sh.which("tor"),
                     os.path.join(base_dir(), "vendor", "linux", "tor", "tor")):
            if cand and os.path.exists(cand):
                return cand
    return os.path.join(base_dir(), "vendor", "tor", "tor.exe")


def pt_bin(name: str) -> str:
    """Pluggable transport: sistema (Linux) → embutido (Windows)."""
    table = {"lyrebird": ("obfs4proxy", "lyrebird", "lyrebird.exe"),
             "conjure": ("conjure-client", "conjure-client", "conjure-client.exe")}
    sys_name, _lin, win = table.get(name, (name, name, name + ".exe"))
    if os.name != "nt":
        import shutil as _sh
        for cand in (_sh.which(sys_name),
                     os.path.join(base_dir(), "vendor", "linux", "tor",
                                  "pluggable_transports", sys_name)):
            if cand and os.path.exists(cand):
                return cand
    return os.path.join(base_dir(), "vendor", "tor", "pluggable_transports", win)


def geoip(base: str, name: str) -> str:
    return os.path.join(base, "vendor", "data", name)


# Países 5/9/14 Olhos (códigos ISO p/ ExcludeExitNodes).
EYES_FIVE = ("us", "gb", "ca", "au", "nz")
EYES_NINE = EYES_FIVE + ("dk", "fr", "nl", "no")
EYES_FOURTEEN = EYES_NINE + ("de", "be", "it", "se", "es")
EYES_MAP = {"five": EYES_FIVE, "nine": EYES_NINE, "fourteen": EYES_FOURTEEN}


def eyes_exclude(mode: str) -> str:
    """'us,gb,...' ou '' (todos)."""
    return ",".join(EYES_MAP.get(mode, ()))


def _tor_file_matches(exe: str, expect_hex: str) -> bool:
    """Compara SHA-256 de um arquivo com o esperado (False em qualquer erro)."""
    try:
        import hashlib as _hl
        with open(exe, "rb") as f:
            return _hl.sha256(f.read()).hexdigest() == (expect_hex or "").lower()
    except OSError:
        return False


class TorWorker(QObject):
    progress = pyqtSignal(float, str, str)      # frac, tag, summary
    connected = pyqtSignal()
    failed = pyqtSignal(str)
    log_line = pyqtSignal(str)
    exit_info = pyqtSignal(str, bool, str)      # ip, is_tor, country
    identity_done = pyqtSignal()
    test_result = pyqtSignal(str, str)          # target, result
    status_result = pyqtSignal(dict)            # check manual de status
    circuit_result = pyqtSignal(list)           # [{id, path:[{fp,nick,ip,cc}]}]

    def __init__(self, cfg: AppConfig):
        super().__init__()
        self.cfg = cfg
        self.lang = cfg.lang
        self._stop = threading.Event()
        self._proc: subprocess.Popen | None = None
        # Buffer volátil do stdout do tor (modo never_store_logs).
        import collections as _cl
        self._stdout_buf: _cl.deque = _cl.deque(maxlen=500)
        self._stdout_lock = threading.Lock()
        self._ctl: Controller | None = None
        self._last_frac = 0.0
        self._last_change = time.time()
        self._tor_data = ""
        import random as _rnd; self._ctl_port = _rnd.randint(49152, 65535)

    def tr(self, key: str) -> str:
        return t(self.lang, key)

    def _push_tordata_note(self, tordata: str) -> None:
        try:
            self.log_line.emit(t(self.lang, "log_tordata").replace("{p}", tordata))
        except RuntimeError:
            pass

    # ---------- torrc ----------
    def _writable_dir(self, path: str) -> bool:
        """Pasta existe e dá p/ criar+apagar arquivo (prova real, não ACL)."""
        try:
            os.makedirs(path, exist_ok=True)
            probe = os.path.join(path, ".wtest")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("1")
            os.remove(probe)
            return True
        except OSError:
            return False

    def _resolve_tordata(self) -> str:
        """Escolhe onde o Tor pode escrever: salvo → padrão → Local → Temp."""
        import tempfile as _tf
        _, data = app_dirs()
        local = os.environ.get("LOCALAPPDATA", data)
        cands = []
        if (self.cfg.tor_data_dir or "").strip():
            cands.append(self.cfg.tor_data_dir.strip())
        cands.append(os.path.join(data, "tor-data"))
        cands.append(os.path.join(local, "anonshield", "Anonymous Shield", "tor-data"))
        cands.append(os.path.join(_tf.gettempdir(), "anonshield-tor-data"))
        for c in cands:
            if self._writable_dir(c):
                return c
        return cands[1]

    def write_torrc(self) -> tuple[str, str]:
        _, data = app_dirs()
        tordata = self._resolve_tordata()
        if tordata != (self.cfg.tor_data_dir or ""):
            self.cfg.tor_data_dir = tordata
            try:
                self.cfg.save()
            except Exception:
                pass
        try:
            self._push_tordata_note(tordata)
        except Exception:
            pass
        self._tor_data = tordata
        base = base_dir()
        lines = [
            f"SocksPort 127.0.0.1:{self.cfg.socks_port}",
            f"ControlPort 127.0.0.1:{self._ctl_port}",
        ]
        try:
            from .sysprotect import app_socks_port as _aport
            _seen = set()
            for _i, _a in enumerate(list(self.cfg.apps or [])[:30]):
                _en = _a.get("enabled", True) if isinstance(_a, dict) else getattr(_a, "enabled", True)
                if not _en:
                    continue
                _p = _aport(_i)
                if _p not in _seen and _p != self.cfg.socks_port:
                    _seen.add(_p)
                    lines.append(f"SocksPort 127.0.0.1:{_p}")
        except Exception:
            pass
        lines += [
            "CookieAuthentication 1",
            f"DataDirectory {tordata}".replace("\\", "/"),
            f"GeoIPFile {geoip(base, 'geoip')}".replace("\\", "/"),
            f"GeoIPv6File {geoip(base, 'geoip6')}".replace("\\", "/"),
            "Log notice file {}".format(os.path.join(tordata, "tor.log").replace("\\", "/"))
            if not self.cfg.never_store_logs else "Log notice stdout",
        ]
        if self.cfg.upstream_enabled and self.cfg.upstream_proxy_url.strip():
            lines += self._upstream_lines(self.cfg.upstream_proxy_url.strip())
        excl = eyes_exclude(self.cfg.exit_mode)
        if excl:
            lines.append(f"ExcludeExitNodes {{{excl}}}")
            lines.append("StrictNodes 1")
        if self.cfg.bridges_enabled and self.cfg.bridges:
            from .sysprotect import bridge_valid as _bv
            _blines = []
            for b in self.cfg.bridges:
                # Anti-injeção: 1 bridge = 1 linha (corta CR/LF/controles).
                b = str(b).split("\n")[0].split("\r")[0].strip()
                b = "".join(c for c in b if c == " " or c == "\t" or ord(c) >= 32)
                b = " ".join(b.split())
                if not b or len(b) > 2000 or b.startswith("#"):
                    continue
                if not b.lower().startswith("bridge "):
                    b = "Bridge " + b
                try:
                    if not _bv(b):
                        continue  # defesa em profundidade: UI valida, torrc filtra
                except Exception:
                    continue
                _blines.append(b)
            if _blines:
                lines.append("UseBridges 1")
                lines.extend(_blines)
            pt = self._pt_line()
            if pt:
                lines.append(pt)
        torrc = os.path.join(tordata, "torrc")
        text = "\n".join(lines) + "\n"
        last: OSError | None = None
        for attempt in range(6):
            try:
                # Escrita atômica: temp único + replace (janela mínima de trava).
                tmp = os.path.join(
                    tordata, f".torrc-{os.getpid()}-{attempt}.tmp")
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(text)
                os.replace(tmp, torrc)
                last = None
                break
            except PermissionError as e:
                last = e
                # 1ª falha: repara ACL; demais: trava transitória
                # (antivírus/indexador/filtro) — espera e tenta de novo.
                if attempt == 0:
                    try:
                        from .sysprotect import acl_repair as _repair
                        _repair(torrc)
                        _repair(tordata)
                    except Exception:
                        pass
                time.sleep(1.0)
        if last is not None:
            # Insistiu: usa torrc único do processo e segue o jogo.
            alt = os.path.join(
                tordata, f"torrc-{os.getpid()}-{int(time.time())}")
            try:
                with open(alt, "w", encoding="utf-8") as f:
                    f.write(text)
                torrc = alt
                self._cleanup_stale_torrc(tordata, keep=alt)
            except OSError:
                from .sysprotect import acl_diag as _diag2
                hint = _diag2(torrc) or _diag2(tordata)
                raise PermissionError(
                    f"{last} | ACL: {hint or '?'}") from last
        try:
            from .sysprotect import lock_private as _lock
            _lock(torrc)  # pode conter credencial de upstream: só o usuário lê
        except Exception:
            pass
        return torrc, tordata

    @staticmethod
    def _cleanup_stale_torrc(tordata: str, keep: str) -> None:
        """Remove torrc-<pid> órfãos de execuções passadas."""
        import time as _t
        try:
            now = _t.time()
            for name in os.listdir(tordata):
                if name.startswith("torrc-") and os.path.join(tordata, name) != keep:
                    p = os.path.join(tordata, name)
                    try:
                        if now - os.path.getmtime(p) > 7 * 86400:
                            os.remove(p)
                    except OSError:
                        pass
        except OSError:
            pass

    @staticmethod
    def _upstream_parts(url: str) -> tuple[str, str, int, str, str]:
        """(scheme, host, port, user, pw) sanitizados. Sem segredo no disco."""
        from urllib.parse import urlparse, unquote
        import re as _re
        u = urlparse(url if "://" in url else "socks5h://" + url)
        user = _re.sub(r"\s+", "", unquote(u.username or ""))[:256]
        pw = _re.sub(r"\s+", "", unquote(u.password or ""))[:256]
        return u.scheme.lower(), u.hostname or "", u.port or 1080, user, pw

    def _upstream_lines(self, url: str) -> list[str]:
        """torrc: SEMPRE sem credencial (vai só host:porta)."""
        try:
            scheme, host, port, _, _ = self._upstream_parts(url)
            if scheme in ("socks5", "socks5h"):
                return [f"Socks5Proxy {host}:{port}"]
            if scheme in ("socks4", "socks4a"):
                return [f"Socks4Proxy {host}:{port}"]
            if scheme in ("http", "https"):
                return [f"HTTPSProxy {host}:{port}"]
        except Exception:
            pass
        return []

    def _upstream_auth(self, url: str) -> list[tuple[str, str]]:
        """Credencial aplicada em runtime via SETCONF (nunca em disco)."""
        try:
            scheme, host, port, user, pw = self._upstream_parts(url)
            if not user:
                return []
            auth = f"{user}:{pw}@" if pw else f"{user}@"
            if scheme in ("socks5", "socks5h"):
                return [("Socks5Proxy", f"{auth}{host}:{port}")]
            if scheme in ("socks4", "socks4a"):
                return [("Socks4Proxy", f"{auth}{host}:{port}")]
            if scheme in ("http", "https"):
                return [("HTTPSProxy", f"{auth}{host}:{port}"),
                        ("HTTPSProxyAuthenticator", f"{user} {pw}".strip())]
        except Exception:
            pass
        return []

    def _pt_line(self) -> str:
        lyrebird = pt_bin("lyrebird")
        conjure = pt_bin("conjure")
        wants_obfs4 = any(b.strip().lower().startswith("obfs4") for b in self.cfg.bridges)
        wants_conjure = any(b.strip().lower().startswith("conjure") for b in self.cfg.bridges)
        custom = (self.cfg.pt_path or "").split("\n")[0].split("\r")[0].strip()
        if wants_obfs4 and os.path.exists(lyrebird) and not custom:
            return f"ClientTransportPlugin obfs4 exec {lyrebird}"
        if wants_conjure and os.path.exists(conjure) and not custom:
            return f"ClientTransportPlugin conjure exec {conjure}"
        if custom and os.path.exists(custom):
            # Formato: "transporte [args] caminho" ou só caminho (assume obfs4).
            parts = custom.split()
            if len(parts) > 1:
                return f"ClientTransportPlugin {' '.join(parts)}"
            name = self.cfg.bridge_preset if self.cfg.bridge_preset not in ("direto", "auto", "custom") else "obfs4"
            return f"ClientTransportPlugin {name} exec {custom}"
        return ""

    # ---------- ciclo ----------
    def run_connect(self) -> None:
        exe = tor_bin()
        if not os.path.exists(exe):
            self.failed.emit(self.tr("tor_fail").replace("{e}", f"tor missing: {exe}"))
            return
        if not self._verify_bundled_tor(exe):
            return
        try:
            torrc, _ = self.write_torrc()
        except OSError as e:
            self.failed.emit(self.tr("tor_fail").replace("{e}", str(e)))
            return
        self.log_line.emit(self.tr("tor_starting"))
        no_disk = bool(self.cfg.never_store_logs)
        if no_disk:
            # Nada em disco: remove tor.log residual antes de subir.
            try:
                old = os.path.join(self._tor_data or "", "tor.log")
                if old and os.path.exists(old):
                    os.remove(old)
            except OSError:
                pass
        try:
            self._proc = subprocess.Popen(
                [exe, "-f", torrc],
                stdout=subprocess.PIPE if no_disk else subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as e:
            self.failed.emit(self.tr("tor_fail").replace("{e}", str(e)))
            return
        if no_disk and self._proc.stdout is not None:
            threading.Thread(target=self._drain_stdout, daemon=True).start()
        # Aguarda control port
        ctl = None
        for _ in range(60):
            if self._stop.is_set():
                return self._cleanup()
            try:
                ctl = Controller.from_port(port=self._ctl_port)
                ctl.authenticate()
                break
            except Exception:
                time.sleep(0.5)
        if ctl is None:
            self.failed.emit(self.tr("tor_fail").replace("{e}", f"control port {self._ctl_port}"))
            return self._cleanup()
        self._ctl = ctl
        # Credencial do upstream SÓ em runtime (torrc nunca tem segredo).
        if self.cfg.upstream_enabled and self.cfg.upstream_proxy_url.strip():
            try:
                for _k, _v in self._upstream_auth(self.cfg.upstream_proxy_url.strip()):
                    ctl.set_conf(_k, _v)
                self.log_line.emit(self.tr("up_auth_ok"))
            except Exception as e:  # noqa: BLE001
                self.failed.emit(self.tr("up_auth_fail").replace("{e}", str(e)[:200]))
                return self._cleanup()
        t0 = time.time()
        try:
            while not self._stop.is_set():
                try:
                    phase = ctl.get_info("status/bootstrap-phase")
                except Exception as e:
                    self.failed.emit(self.tr("tor_bootstrap_fail").replace("{e}", str(e)[:300]))
                    return
                frac, tag, summary = self._parse_phase(phase)
                if abs(frac - self._last_frac) > 0.001:
                    self._last_frac = frac
                    self._last_change = time.time()
                stall = time.time() - self._last_change
                self.progress.emit(frac, tag, summary)
                if frac >= 1.0:
                    self.connected.emit()
                    self._fetch_exit()
                    return  # mantém tor rodando; thread encerra, controle reabre sob demanda
                if time.time() - t0 > 600:
                    self.failed.emit(self.tr("tor_bootstrap_fail").replace("{e}", "timeout 600s"))
                    return
                time.sleep(0.7)
        finally:
            try:
                ctl.close()
            except Exception:
                pass
            self._ctl = None

    @staticmethod
    def _parse_phase(phase: str) -> tuple[float, str, str]:
        frac, tag, summary = 0.0, "", phase.strip().replace("\n", " ")
        for part in phase.replace("\r", "").split():
            if part.startswith("PROGRESS="):
                try:
                    frac = float(part.split("=", 1)[1]) / 100.0
                except ValueError:
                    pass
            elif part.startswith("TAG="):
                tag = part.split("=", 1)[1]
            elif part.startswith("SUMMARY="):
                summary = part.split("=", 1)[1].strip('"')
        return max(0.0, min(1.0, frac)), tag, summary

    def _fetch_exit(self) -> None:
        import requests
        proxies = {"http": f"socks5h://127.0.0.1:{self.cfg.socks_port}",
                   "https": f"socks5h://127.0.0.1:{self.cfg.socks_port}"}
        try:
            r = requests.get("https://check.torproject.org/api/ip", proxies=proxies, timeout=40)
            ip = r.json().get("IP", "?")
            is_tor = bool(r.json().get("IsTor", False))
        except Exception:
            return
        country = ""
        try:
            g = requests.get(f"http://ip-api.com/json/{ip}?fields=country,city",
                             proxies=proxies, timeout=40).json()
            c, city = g.get("country", ""), g.get("city", "")
            country = f"{c}, {city}" if city else c
        except Exception:
            pass
        self.exit_info.emit(ip, is_tor, country)

    def apply_exit_mode(self) -> None:
        """Aplica exit_mode ao vivo via controle (sem reconectar)."""
        excl = eyes_exclude(self.cfg.exit_mode)
        try:
            with Controller.from_port(port=self._ctl_port) as ctl:
                ctl.authenticate()
                if excl:
                    ctl.set_conf("ExcludeExitNodes", "{" + excl + "}")
                    ctl.set_conf("StrictNodes", "1")
                else:
                    ctl.reset_conf("ExcludeExitNodes", "StrictNodes")
            self.log_line.emit(self.tr("exit_applied").replace(
                "{c}", excl if excl else self.tr("exit_all")))
        except Exception as e:  # noqa: BLE001
            self.log_line.emit(f"✗ {e}"[:300])

    @staticmethod
    def _relay_info(ctl, fp: str) -> tuple[str, str]:
        """(ip, código país 2 letras) via GeoIP do próprio Tor."""
        ip, cc = "?", ""
        try:
            desc = ctl.get_network_status(fp)
            ip = getattr(desc, "address", "?") or "?"
        except Exception:
            pass
        if ip and ip != "?":
            try:
                cc = (ctl.get_info(f"ip-to-country/{ip}") or "").strip().lower()
                if len(cc) != 2:
                    cc = ""
            except Exception:
                pass
        return ip, cc

    def fetch_circuit(self) -> None:
        """Circuito ativo (guarda→meio→saída) p/ exibir no dashboard."""
        info: list = []
        fallback: list = []
        try:
            with Controller.from_port(port=self._ctl_port) as ctl:
                ctl.authenticate()
                for circ in ctl.get_circuits():
                    try:
                        if circ.status != "BUILT":
                            continue
                        path = []
                        for fp, nick in (circ.path or [])[:4]:
                            ip, cc = self._relay_info(ctl, fp)
                            path.append({"fp": fp, "nick": nick or "",
                                         "ip": ip, "cc": cc})
                        if len(path) >= 2:
                            entry = {"id": str(circ.id), "path": path}
                            if (circ.purpose or "GENERAL") == "GENERAL":
                                info.append(entry)
                                break
                            if not fallback:
                                fallback.append(entry)
                    except Exception:
                        continue
            if not info:
                info = fallback[:1]
        except Exception:
            pass
        try:
            self.circuit_result.emit(info[:1])
        except RuntimeError:
            pass

    def new_identity(self) -> None:
        try:
            with Controller.from_port(port=self._ctl_port) as ctl:
                ctl.authenticate()
                ctl.signal("NEWNYM")
            self.identity_done.emit()
            self._fetch_exit()
        except Exception as e:
            self.failed.emit(str(e)[:300])

    def status_check(self) -> None:
        """Verificação ativa: fase do bootstrap (controle) + saída IsTor."""
        info: dict = {"phase": "?", "frac": -1.0, "ip": "", "is_tor": False, "err": ""}
        try:
            with Controller.from_port(port=self._ctl_port) as ctl:
                ctl.authenticate()
                frac, tag, _ = self._parse_phase(ctl.get_info("status/bootstrap-phase"))
                info["phase"] = f"{int(frac * 100)}% {tag}".strip()
                info["frac"] = frac
        except Exception as e:  # noqa: BLE001
            info["err"] = f"controle: {e}"[:160]
        try:
            import requests
            proxies = {"http": f"socks5h://127.0.0.1:{self.cfg.socks_port}",
                       "https": f"socks5h://127.0.0.1:{self.cfg.socks_port}"}
            j = requests.get("https://check.torproject.org/api/ip",
                             proxies=proxies, timeout=25).json()
            info["ip"] = str(j.get("IP", "?"))
            info["is_tor"] = bool(j.get("IsTor", False))
        except Exception as e:  # noqa: BLE001
            pre = (info["err"] + " | ") if info["err"] else ""
            info["err"] = (pre + f"saida: {e}"[:160])
        info["ok"] = info["frac"] >= 1.0 and bool(info["is_tor"])
        try:
            self.status_result.emit(info)
        except RuntimeError:
            pass

    def test_target(self, target: str) -> None:
        import requests
        target = target[:253]
        host, _, port = target.rpartition(":")
        if not host:
            host, port = target, "80"
        proxies = {"http": f"socks5h://127.0.0.1:{self.cfg.socks_port}",
                   "https": f"socks5h://127.0.0.1:{self.cfg.socks_port}"}
        try:
            r = requests.get(f"http://{host}/api/ip", proxies=proxies, timeout=40)
            self.test_result.emit(target, r.text[:2000])
        except Exception as e:
            self.test_result.emit(target, f"Erro: {e}"[:500])

    def _verify_bundled_tor(self, exe: str) -> bool:
        """Confere SHA-256 do tor embutido (só bundle; tor do sistema pula).

        Retorna True se OK ou não-aplicável; False + falha emitida se divergir.
        """
        try:
            if os.name == "nt":
                vend = os.path.join(base_dir(), "vendor") + os.sep
                if not os.path.abspath(exe).startswith(os.path.abspath(vend)):
                    return True
            else:
                return True  # Linux: tor do distro, fora do nosso pin
            pinf = os.path.join(base_dir(), "vendor", "TOR_SHA256")
            with open(pinf, encoding="utf-8") as f:
                expect = (f.read().strip().split() or [""])[0].lower()
            if not expect:
                return True
            if _tor_file_matches(exe, expect):
                return True
            self.failed.emit(self.tr("tor_fail").replace(
                "{e}", "tor.exe diverge do SHA-256 publicado (reinstale)"))
            return False
        except OSError as e:
            self.failed.emit(self.tr("tor_fail").replace("{e}", str(e)))
            return False

    def _drain_stdout(self) -> None:
        """Lê o stdout do tor p/ buffer em RAM (modo never_store_logs)."""
        proc = self._proc
        try:
            while proc is not None and proc.stdout is not None:
                chunk = proc.stdout.readline(65536)
                if not chunk:
                    break
                try:
                    line = chunk.decode("utf-8", "replace").strip()
                except Exception:
                    continue
                if line:
                    with self._stdout_lock:
                        self._stdout_buf.append(line[-380:])
        except Exception:
            pass

    def drain_stdout_lines(self) -> list:
        """Esvazia o buffer volátil (chamado pela UI)."""
        try:
            with self._stdout_lock:
                out = list(self._stdout_buf)
                self._stdout_buf.clear()
                return out
        except Exception:
            return []

    def stop(self) -> None:
        self._stop.set()

    def _cleanup(self) -> None:
        try:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=8)
                except Exception:
                    self._proc.kill()
        except Exception:
            pass
        try:
            if self._proc and self._proc.stdout is not None:
                self._proc.stdout.close()
        except Exception:
            pass
        self._proc = None

    def kill_tor(self) -> None:
        self._cleanup()

    def tor_log_path(self) -> str:
        return os.path.join(self._tor_data, "tor.log") if self._tor_data else ""

    def wipe_data(self) -> str:
        self._cleanup()
        n = 0
        if self._tor_data and os.path.isdir(self._tor_data):
            for entry in os.listdir(self._tor_data):
                p = os.path.join(self._tor_data, entry)
                try:
                    if os.path.isdir(p):
                        shutil.rmtree(p, ignore_errors=True)
                    else:
                        os.remove(p)
                    n += 1
                except OSError:
                    pass
        return f"✓ ({n})"


class TorThread(QThread):
    def __init__(self, worker: TorWorker):
        super().__init__()
        self.worker = worker

    def run(self) -> None:
        self.worker.run_connect()


def wait_port(port: int, timeout: float = 3.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=1)
            s.close()
            return True
        except OSError:
            time.sleep(0.2)
    return False
