# Copyright (C) 2026 Abaddon2010
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later
# Licenca dupla: Apache-2.0 OU GPL-3.0-ou-posterior, a sua escolha. Ver LICENSE-APACHE e LICENSE na raiz.

"""Anonymous Shield — sistema: proxy WinINET, firewall, apps, DNSCrypt, testes de rede."""
from __future__ import annotations

import os
import socket
import struct
import subprocess
import random
import time
from dataclasses import dataclass

FW_BLOCK = "AnonShield-BlockAll"
FW_ALLOW = "AnonShield-Allow"
FW_APP = "AnonymousShield"
# Nomes legados (era TorShield): sempre limpos junto na reversão.
FW_LEGACY = ("TorShield-BlockAll", "TorShield-Allow", "TorShield")
INET_KEY = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"


@dataclass
class SysProxy:
    enabled: bool = False
    server: str = ""
    bypass: str = ""


def _run(cmd: list[str], timeout: int = 20) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return p.returncode == 0, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def _reg_query(value: str) -> str | None:
    ok, out = _run(["reg", "query", INET_KEY, "/v", value])
    if not ok:
        return None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith(value):
            parts = line.split()
            if len(parts) >= 3:
                return " ".join(parts[2:])
    return None


def get_proxy() -> SysProxy:
    if os.name != "nt":
        from . import sysprotect_linux as _lx
        return _lx.get_proxy()
    en = _reg_query("ProxyEnable")
    return SysProxy(
        enabled=en in ("0x1", "1"),
        server=_reg_query("ProxyServer") or "",
        bypass=_reg_query("ProxyOverride") or "",
    )


def is_our_proxy(port: int) -> bool:
    p = get_proxy()
    return p.enabled and f"127.0.0.1:{port}" in p.server


def set_proxy(port: int) -> SysProxy:
    if os.name != "nt":
        from . import sysprotect_linux as _lx
        return _lx.set_proxy(port)
    prev = get_proxy()
    for args in (
        ["add", INET_KEY, "/v", "ProxyEnable", "/t", "REG_DWORD", "/d", "1", "/f"],
        ["add", INET_KEY, "/v", "ProxyServer", "/t", "REG_SZ", "/d", f"socks=127.0.0.1:{port}", "/f"],
        ["add", INET_KEY, "/v", "ProxyOverride", "/t", "REG_SZ", "/d", "<local>", "/f"],
    ):
        ok, out = _run(["reg"] + args)
        if not ok:
            raise RuntimeError(out.strip()[:300])
    return prev


def restore_proxy(prev: SysProxy) -> None:
    if os.name != "nt":
        from . import sysprotect_linux as _lx
        _lx.restore_proxy(prev)
        return
    if prev.enabled:
        _run(["reg", "add", INET_KEY, "/v", "ProxyEnable", "/t", "REG_DWORD", "/d", "1", "/f"])
        if prev.server:
            _run(["reg", "add", INET_KEY, "/v", "ProxyServer", "/t", "REG_SZ", "/d", prev.server, "/f"])
        else:
            _run(["reg", "delete", INET_KEY, "/v", "ProxyServer", "/f"])
        if prev.bypass:
            _run(["reg", "add", INET_KEY, "/v", "ProxyOverride", "/t", "REG_SZ", "/d", prev.bypass, "/f"])
        else:
            _run(["reg", "delete", INET_KEY, "/v", "ProxyOverride", "/f"])
    else:
        _run(["reg", "add", INET_KEY, "/v", "ProxyEnable", "/t", "REG_DWORD", "/d", "0", "/f"])


def is_admin() -> bool:
    if os.name != "nt":
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False
    ok, _ = _run(["net", "session"], timeout=10)
    return ok


def net_rescue() -> list[tuple[str, str]]:
    """Botão de pânico / auto-reversão: desfaz tudo que pode travar a net.

    Retorna [(chave_i18n, detalhe)]. Só toca no proxy se for o nosso
    (127.0.0.1); firewall e processos Tor são sempre limpos.
    """
    rep: list[tuple[str, str]] = []
    try:
        firewall_unblock()
    except Exception:
        pass
    rep.append(("rescue_fw", "off" if not firewall_active() else "fail"))
    try:
        p = get_proxy()
        if p.enabled and "127.0.0.1" in (p.server or ""):
            restore_proxy(SysProxy())
            rep.append(("rescue_proxy", "off"))
        else:
            rep.append(("rescue_proxy", "kept"))
    except Exception as e:  # noqa: BLE001
        rep.append(("rescue_proxy", f"fail {e}"[:80]))
    killed = []
    if os.name == "nt":
        for img in ("tor.exe", "dnscrypt-proxy.exe", "lyrebird.exe", "conjure-client.exe"):
            ok, _ = _run(["taskkill", "/F", "/IM", img], timeout=15)
            if ok:
                killed.append(img)
    else:
        for img in ("tor", "obfs4proxy", "lyrebird", "conjure-client", "dnscrypt-proxy"):
            ok, _ = _run(["pkill", "-x", img], timeout=15)
            if ok:
                killed.append(img)
    rep.append(("rescue_killed", ", ".join(killed) if killed else "-"))
    return rep


def _netsh(args: list[str]) -> tuple[bool, str]:
    return _run(["netsh"] + args, timeout=30)


def firewall_active() -> bool:
    if os.name != "nt":
        from . import sysprotect_linux as _lx
        return _lx.firewall_active()
    ok, out = _netsh(["advfirewall", "firewall", "show", "rule", f"name={FW_BLOCK}"])
    if ok and "AnonShield-BlockAll" in out and "No rules match" not in out:
        return True
    ok2, out2 = _netsh(["advfirewall", "firewall", "show", "rule",
                        "name=TorShield-BlockAll"])
    return bool(ok2 and "TorShield-BlockAll" in out2 and "No rules match" not in out2)


def firewall_unblock() -> None:
    if os.name != "nt":
        from . import sysprotect_linux as _lx
        _lx.firewall_unblock()
        return
    _netsh(["advfirewall", "firewall", "delete", "rule", f"name={FW_ALLOW}"])
    for legacy in FW_LEGACY:
        _netsh(["advfirewall", "firewall", "delete", "rule", f"name={legacy}"])


def set_linux_guards(ips) -> list[str]:
    """Registra IPs de guardas p/ o kill-switch nftables (só Linux)."""
    if os.name == "nt":
        return []
    from . import sysprotect_linux as _lx
    return _lx.set_linux_guards(ips)


def refresh_linux_guards() -> bool:
    """Reaplica os sets de guardas sem reconstruir a tabela (só Linux)."""
    if os.name == "nt":
        return False
    from . import sysprotect_linux as _lx
    return _lx.refresh_linux_guards()


def emergency_restore(prev: "SysProxy | dict | None" = None) -> dict:
    """Restaura a internet padrão (uso no botão de emergência e no boot).

    - Proxy: se `prev` for válido, restaura ele; senão, se o proxy atual
      apontar para 127.0.0.1 (nosso SOCKS morto), desliga (ProxyEnable=0).
      Proxy de terceiros é preservado (não tocamos).
    - Firewall: apaga as regras de kill-switch (BlockAll + Allow).
    Retorna {"proxy": str, "firewall": str} com resumo curto.
    """
    res = {"proxy": "ok", "firewall": "ok"}
    try:
        use_prev = None
        if isinstance(prev, dict):
            try:
                use_prev = SysProxy(
                    enabled=bool(prev.get("enabled", False)),
                    server=str(prev.get("server", "") or ""),
                    bypass=str(prev.get("bypass", "") or ""),
                )
            except Exception:
                use_prev = None
        elif isinstance(prev, SysProxy):
            use_prev = prev
        if use_prev is not None:
            restore_proxy(use_prev)
            res["proxy"] = "anterior restaurado"
        else:
            try:
                cur = get_proxy()
            except Exception:
                cur = SysProxy()
            if cur.enabled and ("127.0.0.1" in (cur.server or "")):
                restore_proxy(SysProxy(enabled=False))
                res["proxy"] = "proxy local desligado"
            elif cur.enabled:
                res["proxy"] = "proxy de terceiros mantido"
            else:
                # Garante desligado mesmo se o reg estiver inconsistente.
                try:
                    _run(["reg", "add", INET_KEY, "/v", "ProxyEnable",
                          "/t", "REG_DWORD", "/d", "0", "/f"])
                except Exception:
                    pass
                res["proxy"] = "já direto"
    except Exception as e:  # noqa: BLE001
        res["proxy"] = f"falha: {e}"[:120]
    try:
        firewall_unblock()
    except Exception as e:  # noqa: BLE001
        res["firewall"] = f"falha: {e}"[:120]
    return res


def firewall_block(extra_allow: str = "") -> None:
    if os.name != "nt":
        # Linux: kill-switch nftables por IPs de guardas (extra_allow por
        # programa não se aplica; root via pkexec).
        from . import sysprotect_linux as _lx
        _lx.firewall_block()
        return
    if not is_admin():
        raise PermissionError("admin-required")
    import sys as _sys
    exe = os.path.abspath(_sys.argv[0])
    if '"' in exe:
        raise RuntimeError("bad exe path")
    allows = [exe] + [e.strip() for e in (extra_allow or "").split(";") if e.strip()]
    allows = [a for a in allows if '"' not in a]
    firewall_unblock()
    for prog in allows:
        ok, out = _netsh(["advfirewall", "firewall", "add", "rule", f"name={FW_ALLOW}",
                          "dir=out", "action=allow", f'program="{prog}"',
                          "enable=yes", "profile=any"])
        if not ok:
            raise RuntimeError(out.strip()[:300])
    ok, out = _netsh(["advfirewall", "firewall", "add", "rule", f"name={FW_BLOCK}",
                      "dir=out", "action=block", "enable=yes", "profile=any"])
    if not ok:
        raise RuntimeError(out.strip()[:300])


def ensure_allowed_app() -> bool:
    """Garante regras IN+OUT do Firewall p/ o exe atual. True se criou/verificou."""
    if os.name != "nt":
        return True  # nftables não precisa de allow por programa
    if not is_admin():
        return False
    import sys as _sys
    exe = os.path.abspath(_sys.argv[0])

    def has(direction: str) -> bool:
        ok, out = _netsh(["advfirewall", "firewall", "show", "rule",
                          f"name={FW_APP}", f"dir={direction}"])
        return ok and (exe in out or FW_APP in out)

    if has("in") and has("out"):
        return True
    _netsh(["advfirewall", "firewall", "delete", "rule", f"name={FW_APP}"])
    _netsh(["advfirewall", "firewall", "delete", "rule", "name=TorShield"])
    if not has("in"):
        ok, out = _netsh(["advfirewall", "firewall", "add", "rule", f"name={FW_APP}",
                          "dir=in", "action=allow", f'program="{exe}"',
                          "enable=yes", "profile=any"])
        if not ok:
            raise RuntimeError(out.strip()[:300])
    if not has("out"):
        ok, out = _netsh(["advfirewall", "firewall", "add", "rule", f"name={FW_APP}",
                          "dir=out", "action=allow", f'program="{exe}"',
                          "enable=yes", "profile=any"])
        if not ok:
            raise RuntimeError(out.strip()[:300])
    return True


# ---------------- VPN ----------------

VPN_KNOWN = {
    "nordvpn.exe": "NordVPN",
    "expressvpn.exe": "ExpressVPN",
    "protonvpn.exe": "ProtonVPN",
    "protonvpn-wireguard.exe": "ProtonVPN-WG",
    "mullvad-vpn.exe": "Mullvad",
    "surfshark.exe": "Surfshark",
    "pia-client.exe": "PIA",
    "wireguard.exe": "WireGuard",
    "openvpn.exe": "OpenVPN",
    "openvpn-gui.exe": "OpenVPN-GUI",
    "tap-windows.exe": "TAP",
}


def vpn_running() -> list[dict]:
    """VPNs em execução: [{name, exe}]. Rápido (tasklist/pgrep) + paths."""
    if os.name != "nt":
        from . import sysprotect_linux as _lx
        return _lx.vpn_running()
    ok, out = _run(["tasklist", "/FO", "CSV", "/NH"], timeout=15)
    if not ok:
        return []
    found: dict[str, None] = {}
    for line in out.splitlines():
        if not line.startswith('"'):
            continue
        img = line.split('","')[0].strip('"').lower()
        if img in VPN_KNOWN:
            found[img] = None
    if not found:
        return []
    cond = " or ".join(f"Name='{n}'" for n in found)
    ok2, out2 = _run(["powershell", "-NoProfile", "-Command",
                      f"Get-CimInstance Win32_Process -Filter \"{cond}\""
                      " | Select-Object Name,ExecutablePath"
                      " | ConvertTo-Csv -NoTypeInformation"], timeout=25)
    res: list[dict] = []
    if ok2:
        import csv as _csv
        import io as _io
        try:
            for row in _csv.DictReader(_io.StringIO(out2)):
                name = (row.get("Name") or "").lower()
                exe = row.get("ExecutablePath") or ""
                if name in VPN_KNOWN:
                    res.append({"name": VPN_KNOWN[name], "exe": exe})
        except Exception:
            pass
    if not res:
        res = [{"name": VPN_KNOWN[n], "exe": ""} for n in found]
    seen, uniq = set(), []
    for r in res:
        if r["name"] not in seen:
            seen.add(r["name"])
            uniq.append(r)
    return uniq


def find_openvpn() -> str:
    import shutil as _sh
    for cand in (
        _sh.which("openvpn"),
        r"C:\Program Files\OpenVPN\bin\openvpn.exe",
        r"C:\Program Files (x86)\OpenVPN\bin\openvpn.exe",
    ):
        if cand and os.path.exists(cand):
            return cand
    return ""


def authenticode(path: str) -> str | None:
    """Assinatura digital EMBUTIDA (Windows, PE): 'valid'|'none'|'bad'|None.

    Leitura apenas — informa, não bloqueia. Limitação honesta: binários
    assinados só via catálogo (ex. notepad.exe) retornam 'none'; para
    instaladores de release (assinatura embutida) o check é exato.
    """
    if os.name != "nt":
        return None
    if not path.lower().endswith((".exe", ".msi", ".dll", ".sys")):
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class _GUID(ctypes.Structure):
            _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                        ("Data3", wintypes.WORD), ("Data4", wintypes.BYTE * 8)]

        class _FILE(ctypes.Structure):
            _fields_ = [("cbStruct", wintypes.DWORD),
                        ("pcwszFilePath", wintypes.LPCWSTR),
                        ("hFile", wintypes.HANDLE),
                        ("pgKnownSubject", ctypes.c_void_p)]

        class _DATA(ctypes.Structure):
            _fields_ = [("cbStruct", wintypes.DWORD),
                        ("pPolicyCallbackData", ctypes.c_void_p),
                        ("pSIPClientData", ctypes.c_void_p),
                        ("dwUIChoice", wintypes.DWORD),
                        ("fdwRevocationChecks", wintypes.DWORD),
                        ("dwUnionChoice", wintypes.DWORD),
                        ("pFile", ctypes.POINTER(_FILE)),
                        ("dwStateAction", wintypes.DWORD),
                        ("hWVTStateData", wintypes.HANDLE),
                        ("pwszURLReference", wintypes.LPCWSTR),
                        ("dwProvFlags", wintypes.DWORD),
                        ("dwUIContext", wintypes.DWORD)]

        action = _GUID(0x00AAC56B, 0xCD44, 0x11D0,
                       (0x8C, 0xC2, 0x00, 0xC0, 0x4F, 0xC2, 0x95, 0xEE))
        fi = _FILE(ctypes.sizeof(_FILE), path, None, None)
        dt = _DATA()
        dt.cbStruct = ctypes.sizeof(_DATA)
        dt.dwUIChoice = 2
        dt.dwUnionChoice = 1
        dt.pFile = ctypes.pointer(fi)
        rc = ctypes.WinDLL("wintrust").WinVerifyTrust(
            None, ctypes.byref(action), ctypes.byref(dt))
        if rc == 0:
            return "valid"
        if rc & 0xFFFFFFFF in (0x800B0100, 0x800B0101):
            return "none"
        return "bad"
    except Exception:
        return None


_TOR_VER_CACHE: str | None = None


def system_dns() -> str:
    """Primeiro DNS IPv4 da interface ativa (só leitura)."""
    if os.name != "nt":
        from . import sysprotect_linux as _lx
        return _lx.system_dns()
    try:
        ok, out = _run(["powershell", "-NoProfile", "-Command",
                        "Get-DnsClientServerAddress -AddressFamily IPv4 | "
                        "Where-Object {$_.ServerAddresses} | "
                        "Select-Object -First 1 -ExpandProperty ServerAddresses"],
                       timeout=15)
        if ok:
            import re as _re
            m = _re.search(r"\d+\.\d+\.\d+\.\d+", out or "")
            if m:
                return m.group(0)
    except Exception:
        pass
    return ""


def socks_live(ports: list[int]) -> list[dict]:
    """Quem está passando pelo Tor AGORA: [{pid, name, port}].

    Varre conexões TCP com um dos ports SOCKS e resolve PID→nome.
    Best-effort (netstat+tasklist no Win; ss no Linux; só leitura).
    """
    if os.name != "nt":
        from . import sysprotect_linux as _lx
        return _lx.socks_live(ports)
    out: list[dict] = []
    try:
        wanted = {int(p) for p in (ports or [])}
        if not wanted:
            return out
        ok, txt = _run(["netstat", "-ano", "-p", "TCP"], timeout=20)
        if not ok:
            return out
        import re as _re
        hits: dict[int, set] = {}
        for line in (txt or "").splitlines():
            parts = line.split()
            if len(parts) < 5 or parts[0] != "TCP":
                continue
            try:
                lp = int(parts[1].rsplit(":", 1)[-1].strip("[]"))
                rp = int(parts[2].rsplit(":", 1)[-1].strip("[]"))
                pid = int(parts[-1])
            except (ValueError, IndexError):
                continue
            use = lp if lp in wanted else (rp if rp in wanted else 0)
            if use and parts[3] == "ESTABLISHED":
                hits.setdefault(pid, set()).add(use)
        if not hits:
            return out
        names: dict[int, str] = {}
        ok2, txt2 = _run(["tasklist", "/FO", "CSV", "/NH"], timeout=20)
        if ok2:
            for line in (txt2 or "").splitlines():
                cols = [c.strip().strip('"') for c in line.split('","')]
                if len(cols) >= 2:
                    try:
                        names[int(cols[1])] = cols[0]
                    except ValueError:
                        pass
        for pid, ps in sorted(hits.items()):
            out.append({"pid": pid, "name": names.get(pid, "?"),
                        "ports": sorted(ps)})
    except Exception:
        pass
    return out


def license_files() -> list[tuple[str, str]]:
    """[(rótulo, caminho)] dos textos de licença: próprias + embutidas (vendor/docs)."""
    out: list[tuple[str, str]] = []
    try:
        from .torctl import base_dir as _bd
        bd = _bd()
        for fname, label in (("LICENSE-APACHE", "Anonymous Shield (Apache-2.0)"),
                             ("LICENSE", "Anonymous Shield (GPL-3.0)")):
            for cand in (os.path.join(bd, fname),
                         os.path.join(os.path.dirname(bd), fname)):
                if os.path.exists(cand):
                    out.append((label, cand))
                    break
        docs = os.path.join(bd, "vendor", "docs")
        labels = {"tor.txt": "Tor (BSD-3)", "openssl.txt": "OpenSSL (Apache-2.0)",
                  "libevent.txt": "libevent (BSD-3)", "zlib.txt": "zlib",
                  "lyrebird.txt": "Lyrebird (obfs4)", "conjure.txt": "Conjure"}
        for name in ("tor.txt", "openssl.txt", "libevent.txt", "zlib.txt",
                     "lyrebird.txt", "conjure.txt"):
            p = os.path.join(docs, name)
            if os.path.exists(p):
                out.append((labels.get(name, name), p))
        return out
    except Exception:
        return out


def read_license(path: str, limit: int = 100000) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except OSError as e:
        return f"✗ {e}"


def tor_version() -> str:
    """Versão do tor.exe embutido (cache). Ex.: '0.4.9.12'."""
    global _TOR_VER_CACHE
    if _TOR_VER_CACHE is not None:
        return _TOR_VER_CACHE
    ver = "?"
    try:
        from .torctl import tor_bin
        import subprocess as _sp
        exe = tor_bin()
        if exe and os.path.exists(exe):
            p = _sp.run([exe, "--version"], capture_output=True, text=True,
                        timeout=15,
                        creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0))
            import re as _re
            m = _re.search(r"Tor version (\d+\.\d+\.\d+\.\d+)", p.stdout or "")
            if m:
                ver = m.group(1)
    except Exception:
        pass
    _TOR_VER_CACHE = ver
    return ver


def ovpn_log_path() -> str:
    from .config import app_dirs
    _, data = app_dirs()
    return os.path.join(data, "openvpn.log")


def acl_reset(path: str) -> None:
    """Restaura a ACL herdada (desfaz lock_private; auto-reparo)."""
    try:
        if os.name == "nt" and os.path.exists(path):
            import subprocess as _sp
            _sp.run(["icacls", path, "/reset"],
                    capture_output=True, timeout=20,
                    creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0))
    except Exception:
        pass


def acl_repair(path: str) -> None:
    """Reparo à prova de ACE nula: reseta a herança E concede F explícito
    ao usuário atual (aditivo — nunca remove nada, nunca trava)."""
    try:
        if os.name != "nt" or not os.path.exists(path):
            return
        import subprocess as _sp
        nowin = getattr(_sp, "CREATE_NO_WINDOW", 0)
        _sp.run(["icacls", path, "/reset"], capture_output=True,
                timeout=20, creationflags=nowin)
        user = os.environ.get("USERNAME", "")
        if user:
            _sp.run(["icacls", path, "/grant", f"{user}:F"],
                    capture_output=True, timeout=20, creationflags=nowin)
    except Exception:
        pass


def acl_diag(path: str, limit: int = 220) -> str:
    """Resumo curto da ACL p/ diagnóstico (retorna '' se não der)."""
    try:
        if os.name == "nt" and os.path.exists(path):
            import subprocess as _sp
            r = _sp.run(["icacls", path], capture_output=True, text=True,
                        timeout=20,
                        creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0))
            out = " ".join((r.stdout or "").split())
            return out[:limit]
    except Exception:
        pass
    return ""


def lock_private(path: str) -> None:
    """Best-effort: arquivo discreto (oculto no Win, 0o600 no POSIX).

    NÃO mexe em herança de ACL: `icacls /inheritance:r` travou o torrc com
    Erro 13 ao rodar como administrador (v1.3.1). A pasta do perfil já
    restringe a SYSTEM/Admin/dono. `acl_reset()` segue existindo para
    reparar arquivos travados pela v1.3.1.
    """
    try:
        if os.name == "nt":
            import ctypes as _ct
            _ct.windll.kernel32.SetFileAttributesW(path, 2)  # hidden
        else:
            os.chmod(path, 0o600)
    except Exception:
        pass


def ovpn_auth_path() -> str:
    from .config import app_dirs
    _, data = app_dirs()
    return os.path.join(data, "ovpn-auth.txt")


def ovpn_shred_auth() -> None:
    """Tritura o arquivo de credenciais (chamado após o openvpn ler)."""
    try:
        from . import vault as _v
        _v.shred(ovpn_auth_path())
    except Exception:
        pass


def _ovpn_free_port() -> int:
    import socket as _s
    s = _s.socket(_s.AF_INET, _s.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])
    finally:
        try:
            s.close()
        except OSError:
            pass


def _ovpn_mgmt_handshake(sock, user: str, password: str, timeout: float = 30.0) -> None:
    """Responde username/password via management (sem arquivo em disco).

    Protocolo: espera `PASSWORD:Need 'Auth'`, envia credenciais, libera hold.
    Levanta RuntimeError em falha/timeout.
    """
    import socket as _sk
    import time as _t
    sock.settimeout(2.0)
    rfile = sock.makefile("rwb", buffering=0)
    try:
        deadline = _t.monotonic() + timeout
        sent_auth = False
        while _t.monotonic() < deadline:
            try:
                raw = rfile.readline(4096)
            except (_sk.timeout, OSError) as e:
                raise RuntimeError(f"mgmt timeout: {e}")
            if not raw:
                raise RuntimeError("mgmt fechou a conexão")
            low = raw.decode("utf-8", "replace").strip()
            if not sent_auth and "PASSWORD:Need 'Auth'" in low:
                rfile.write(f'username "Auth" "{user}"\n'.encode("utf-8", "replace"))
                rfile.write(f'password "Auth" "{password}"\n'.encode("utf-8", "replace"))
                rfile.flush()
                sent_auth = True
            if "HOLD:Waiting for hold release" in low:
                if sent_auth or not user:
                    rfile.write(b"hold release\n")
                    rfile.flush()
                    return
            if "PASSWORD:Verification Failed" in low:
                raise RuntimeError("VPN: usuário/senha rejeitados")
            if "SUCCESS: hold release succeeded" in low:
                return
        raise RuntimeError("mgmt: handshake incompleto (timeout)")
    finally:
        try:
            rfile.close()
        except OSError:
            pass


def _ovpn_mgmt_thread(port: int, user: str, password: str) -> None:
    import socket as _sk
    import time as _t
    deadline = _t.monotonic() + 60.0
    while _t.monotonic() < deadline:
        try:
            s = _sk.create_connection(("127.0.0.1", port), timeout=3)
            break
        except OSError:
            _t.sleep(0.5)
    else:
        return
    try:
        _ovpn_mgmt_handshake(s, user, password)
    except Exception:
        try:
            s.close()
        except OSError:
            pass


def ovpn_start(exe: str, config: str, user: str, password: str):
    """Inicia openvpn --config (exige admin p/ TAP/rotas). Retorna Popen.

    Credenciais NUNCA tocam o disco: vão via management interface
    (127.0.0.1, porta efêmera) em thread dedicada. Sem user, sem auth.
    """
    import subprocess as _sp
    import threading as _th
    args = [exe, "--config", config]
    if user:
        port = _ovpn_free_port()
        args += ["--management", "127.0.0.1", str(port),
                 "--management-query-passwords", "--management-hold",
                 "--auth-nocache", "--log", ovpn_log_path(), "--verb", "3"]
        proc = _sp.Popen(args, stdout=_sp.DEVNULL, stderr=_sp.STDOUT,
                         creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0))
        _th.Thread(target=_ovpn_mgmt_thread,
                   args=(port, user, password or ""), daemon=True).start()
        return proc
    args += ["--log", ovpn_log_path(), "--verb", "3"]
    return _sp.Popen(args, stdout=_sp.DEVNULL, stderr=_sp.STDOUT,
                     creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0))


# ---------------- apps ----------------

def _env_path(var: str, rest: str) -> str | None:
    base = os.environ.get(var)
    if not base:
        return None
    p = os.path.join(base, *rest.split("\\"))
    if not os.path.exists(p):
        return None
    return portable(p)


_PORTABLE_VARS = ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA", "APPDATA")


def bridge_lines_from(text: str) -> list:
    """Extrai linhas de bridge (obfs4/webtunnel/snowflake/Bridge) de um texto."""
    import re as _re
    out = []
    for ln in (text or "").splitlines():
        s = ln.strip()
        if s and _re.match(r"(?i)^(obfs4|webtunnel|snowflake|bridge)\s+\S", s):
            out.append(s)
    return out


def bridge_valid(line: str) -> bool:
    """Uma bridge válida tem transporte + host:porta + fingerprint (40 hex)."""
    import re as _re
    s = (line or "").strip()
    if s.lower().startswith("bridge "):
        s = s[7:].strip()
    return bool(_re.match(
        r"(?i)^(obfs4|webtunnel|snowflake)\s+"
        r"(\[[0-9a-f:]+\]|[\w.-]+):\d+\s+[0-9a-f]{40}\b", s))


def portable(path: str) -> str:
    """Troca prefixo de pasta conhecida por %VAR% (sem nome de usuário)."""
    for var in _PORTABLE_VARS:
        base = os.environ.get(var)
        if base and (path == base or path.startswith(base + os.sep)):
            return f"%{var}%" + path[len(base):]
    return path


def expand(path: str) -> str:
    """Resolve %VAR% de volta para o caminho real."""
    return os.path.expandvars(path)


def detect_apps() -> list[dict]:
    out = []

    def add(name: str, p: str | None) -> None:
        if p:
            out.append({"name": name, "path": p, "enabled": True, "custom": False})

    if os.name != "nt":
        import shutil as _sh
        for name, bins in (
            ("Chrome", ("google-chrome", "google-chrome-stable", "chrome")),
            ("Chromium", ("chromium", "chromium-browser")),
            ("Firefox", ("firefox",)),
            ("Brave", ("brave", "brave-browser")),
            ("Edge", ("microsoft-edge",)),
            ("Discord", ("discord",)),
            ("Telegram", ("telegram-desktop", "telegram")),
        ):
            for b in bins:
                p = _sh.which(b)
                if p:
                    add(name, p)
                    break
        return out

    add("Chrome", _env_path("PROGRAMFILES", r"Google\Chrome\Application\chrome.exe")
        or _env_path("LOCALAPPDATA", r"Google\Chrome\Application\chrome.exe"))
    add("Edge", _env_path("PROGRAMFILES", r"Microsoft\Edge\Application\msedge.exe")
        or _env_path("PROGRAMFILES(X86)", r"Microsoft\Edge\Application\msedge.exe"))
    add("Firefox", _env_path("PROGRAMFILES", r"Mozilla Firefox\firefox.exe")
        or _env_path("PROGRAMFILES(X86)", r"Mozilla Firefox\firefox.exe"))
    add("Brave", _env_path("PROGRAMFILES", r"BraveSoftware\Brave-Browser\Application\brave.exe")
        or _env_path("LOCALAPPDATA", r"BraveSoftware\Brave-Browser\Application\brave.exe"))
    add("Discord", _env_path("LOCALAPPDATA", r"Discord\Update.exe"))
    add("Telegram", _env_path("APPDATA", r"Telegram Desktop\Telegram.exe"))
    return out


_CHROMIUM_EXES = ("chrome.exe", "msedge.exe", "brave.exe", "opera.exe",
                  "vivaldi.exe", "arc.exe",
                  "chrome", "chromium", "chromium-browser", "google-chrome",
                  "google-chrome-stable", "msedge", "microsoft-edge",
                  "brave", "brave-browser", "opera", "vivaldi")
_FIREFOX_EXES = ("firefox.exe", "firefox")


def _tor_profile_dir(kind: str) -> str:
    from .config import app_dirs
    _, data = app_dirs()
    prof = os.path.join(data, f"{kind}-tor-profile")
    os.makedirs(prof, exist_ok=True)
    return prof


def _firefox_tor_profile(port: int) -> str:
    """Perfil Firefox dedicado p/ Tor (não toca no perfil do usuário)."""
    prof = _tor_profile_dir("ff")
    prefs = (
        'user_pref("network.proxy.type", 1);\n'
        'user_pref("network.proxy.socks", "127.0.0.1");\n'
        f'user_pref("network.proxy.socks_port", {int(port)});\n'
        'user_pref("network.proxy.socks_version", 5);\n'
        'user_pref("network.proxy.socks_remote_dns", true);\n'
        'user_pref("network.proxy.no_proxies_on", "localhost, 127.0.0.1");\n'
        # Anti-vazamento: WebRTC DESLIGADO + DoH off (DNS sai pelo SOCKS).
        'user_pref("media.peerconnection.enabled", false);\n'
        'user_pref("network.trr.mode", 5);\n'
        'user_pref("browser.aboutwelcome.enabled", false);\n'
    )
    with open(os.path.join(prof, "user.js"), "w", encoding="utf-8") as f:
        f.write(prefs)
    return prof


APP_SOCKS_BASE = 9160  # 9150 = principal, 9151 = controle


def app_socks_port(i: int) -> int:
    """Porta SOCKS dedicada do app nº i (circuito próprio)."""
    try:
        return APP_SOCKS_BASE + max(0, int(i))
    except (TypeError, ValueError):
        return APP_SOCKS_BASE


def launch_with_proxy(path: str, port: int, url: str = "") -> str:
    """Abre o app FORÇANDO o proxy Tor. Retorna descrição do método usado.

    - Chromium (Chrome/Edge/Brave/...): `--proxy-server` + perfil Tor
      dedicado + WebRTC só pelo proxy (anti-vazamento de IP real).
    - Firefox: perfil Tor dedicado via `user.js` (WebRTC off, sem DoH).
    - Demais: variável `ALL_PROXY` (funciona p/ curl, python, etc.).
    """
    real = expand(path)
    if not real or not os.path.exists(real):
        raise RuntimeError(f"não encontrado: {path}")
    base = os.path.basename(real).lower()
    nowin = getattr(subprocess, "DETACHED_PROCESS", 0)

    def _spawn(args: list, env=None) -> None:
        try:
            subprocess.Popen(args, env=env or dict(os.environ),
                             close_fds=False, creationflags=nowin)
        except OSError as e:
            raise RuntimeError(f"abrir {path}: {e}")

    extra = [url] if url else []
    if base in _CHROMIUM_EXES:
        prof = _tor_profile_dir("chrome")
        if not extra:
            # Página inicial identificada: ninguém confunde com o Chrome normal.
            home = os.path.join(prof, "tor-home.html")
            try:
                with open(home, "w", encoding="utf-8") as f:
                    f.write("<html><body style='background:#1e1b4b;color:#fff;"
                            "font-family:sans-serif;text-align:center;padding-top:15%'>"
                            "<h1>\U0001F9C5 Anonymous Shield — janela Tor</h1>"
                            "<p>Esta janela usa a rede Tor. Seu Chrome normal continua igual.</p>"
                            "</body></html>")
                extra = [home]
            except OSError:
                pass
        _spawn([real, f"--proxy-server=socks5://127.0.0.1:{port}",
                "--enforce-webrtc-ip-handling-policy=disable_non_proxied_udp",
                f"--user-data-dir={prof}", "--no-first-run", "--new-window",
                *extra])
        return "perfil Tor dedicado + --proxy-server + anti-WebRTC"
    if base in _FIREFOX_EXES:
        prof = _firefox_tor_profile(port)
        _spawn([real, "-profile", prof, "-no-remote", "-new-instance", *extra])
        return "perfil Firefox Tor (WebRTC off)"
    env = dict(os.environ)
    socks = f"socks5h://127.0.0.1:{port}"
    env["ALL_PROXY"] = socks
    env["all_proxy"] = socks
    _spawn([real, *extra], env=env)
    return "variável ALL_PROXY"


# ---------------- DNS via stub (stdlib, sem deps) ----------------

def _dns_packet(host: str) -> bytes:
    txid = random.randint(0, 65535)
    header = struct.pack(">HHHHHH", txid, 0x0100, 1, 0, 0, 0)
    qname = b"".join(bytes([len(p)]) + p.encode() for p in host.strip(".").split(".")) + b"\x00"
    return header + qname + struct.pack(">HH", 1, 1), txid


def dns_via_stub(host: str, port: int, timeout: float = 6.0) -> list[str]:
    pkt, txid = _dns_packet(host)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.sendto(pkt, ("127.0.0.1", port))
        data, _ = s.recvfrom(512)
    finally:
        s.close()
    if len(data) < 12 or struct.unpack(">H", data[:2])[0] != txid:
        raise RuntimeError("bad txid")
    ancount = struct.unpack(">H", data[6:8])[0]
    if ancount == 0:
        raise RuntimeError("empty")
    # pula pergunta
    i = 12
    while data[i] != 0:
        i += data[i] + 1
    i += 5
    ips = []
    for _ in range(ancount):
        if data[i] & 0xC0 == 0xC0:
            i += 2
        else:
            while data[i] != 0:
                i += data[i] + 1
            i += 1
        rtype, _, _, rdlen = struct.unpack(">HHIH", data[i:i + 10])
        i += 10
        rdata = data[i:i + rdlen]
        i += rdlen
        if rtype == 1 and rdlen == 4:
            ips.append(socket.inet_ntoa(rdata))
        elif rtype == 28 and rdlen == 16:
            ips.append(socket.inet_ntop(socket.AF_INET6, rdata))
    if not ips:
        raise RuntimeError("no A/AAAA")
    return ips


# ---------------- testes de rede ----------------

def test_direct_net_full() -> dict:
    """DNS + TCP 443 + HTTP sem Tor. Retorna dict c/ ok/latências + texto.

    {"dns_ok","dns_ip","dns_ms","tcp_ok","tcp_ms","http_ok","http_code",
     "http_ms","text"} — ms em float ou None.
    """
    import time as _t
    d: dict = {"dns_ok": False, "dns_ip": "", "dns_ms": None,
               "tcp_ok": False, "tcp_ms": None,
               "http_ok": False, "http_code": "", "http_ms": None}
    out = []
    try:
        t0 = _t.monotonic()
        infos = socket.getaddrinfo("check.torproject.org", 443, type=socket.SOCK_STREAM)
        addr = infos[0][4][0]
        d.update(dns_ok=True, dns_ip=addr, dns_ms=( _t.monotonic() - t0) * 1000.0)
        out.append(f"✓ DNS → {addr}")
    except OSError as e:
        out.append(f"✗ DNS falhou: {e}")
        addr = "check.torproject.org"
    try:
        t0 = _t.monotonic()
        s = socket.create_connection((addr, 443), timeout=10)
        s.close()
        d.update(tcp_ok=True, tcp_ms=(_t.monotonic() - t0) * 1000.0)
        out.append(f"✓ TCP 443 OK ({addr})")
    except OSError as e:
        out.append(f"✗ TCP 443 falhou: {e}")
    try:
        t0 = _t.monotonic()
        s = socket.create_connection(("check.torproject.org", 80), timeout=10)
        s.sendall(b"GET /api/ip HTTP/1.1\r\nHost: check.torproject.org\r\nConnection: close\r\n\r\n")
        data = b""
        s.settimeout(10)
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
        s.close()
        head = data.decode("utf-8", "replace")[:300]
        import re as _re
        m = _re.search(r"HTTP/1\.[01]\s+(\d+)", head)
        d.update(http_ok=True, http_code=m.group(1) if m else "?",
                 http_ms=(_t.monotonic() - t0) * 1000.0)
        out.append(f"✓ HTTP OK:\n{head}")
    except OSError as e:
        out.append(f"✗ HTTP falhou: {e}")
    d["text"] = "\n".join(out)
    return d


def test_direct_net() -> str:
    """DNS + TCP 443 + HTTP sem Tor. Linhas técnicas universais (✓/✗)."""
    return test_direct_net_full()["text"]


def tor_data_size_mb(path: str) -> float:
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return round(total / 1048576, 1)
