# Copyright (C) 2026 Abaddon2010
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later
# Licenca dupla: Apache-2.0 OU GPL-3.0-ou-posterior, a sua escolha. Ver LICENSE-APACHE e LICENSE na raiz.

"""Anonymous Shield — implementações Linux (Debian/Ubuntu): proxy GNOME,
kill-switch nftables, sondas POSIX. Importado sob demanda (só em posix)."""
from __future__ import annotations

import ipaddress
import os
import shutil
import subprocess
import tempfile


TABLE = "anonshield"


def _run(cmd: list[str], timeout: int = 20) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode == 0, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def _have(prog: str) -> bool:
    return shutil.which(prog) is not None


# ---------- proxy (GNOME gsettings) ----------

def _gsettings() -> None:
    if not _have("gsettings"):
        raise RuntimeError("gsettings ausente (proxy manual só em GNOME)")


def get_proxy():
    from .sysprotect import SysProxy as _SP
    try:
        _gsettings()
        ok, mode = _run(["gsettings", "get", "org.gnome.system.proxy", "mode"])
        mode = (mode or "").strip().strip("'")
        okh, host = _run(["gsettings", "get", "org.gnome.system.proxy.socks", "host"])
        okp, port = _run(["gsettings", "get", "org.gnome.system.proxy.socks", "port"])
        host = (host or "").strip().strip("'")
        try:
            port_i = int((port or "0").strip())
        except ValueError:
            port_i = 0
        server = f"socks={host}:{port_i}" if host and port_i else ""
        return _SP(enabled=(mode == "manual" and bool(server)), server=server, bypass="")
    except Exception:
        return _SP(enabled=False)


def set_proxy(port: int):
    from .sysprotect import SysProxy as _SP
    _gsettings()
    prev = get_proxy()
    base = ["gsettings", "set", "org.gnome.system.proxy"]
    for args in (
        base + ["mode", "manual"],
        base + ["socks", "host", "127.0.0.1"],
        base + ["socks", "port", str(int(port))],
        base + ["ignore-hosts", "['localhost', '127.0.0.0/8']"],
    ):
        ok, out = _run(args)
        if not ok:
            raise RuntimeError(out.strip()[:300])
    return prev


def restore_proxy(prev) -> None:
    _gsettings()
    base = ["gsettings", "set", "org.gnome.system.proxy"]
    if prev is not None and getattr(prev, "enabled", False):
        host, port = "127.0.0.1", "9150"
        try:
            srv = (getattr(prev, "server", "") or "").replace("socks=", "")
            if ":" in srv:
                host, port = srv.rsplit(":", 1)
                int(port)
        except (ValueError, AttributeError):
            pass
        _run(base + ["mode", "manual"])
        _run(base + ["socks", "host", host or "127.0.0.1"])
        _run(base + ["socks", "port", port or "9150"])
    else:
        _run(base + ["mode", "none"])


# ---------- firewall kill-switch (nftables) ----------

_GUARDS_V4: list[str] = []
_GUARDS_V6: list[str] = []


def set_linux_guards(ips) -> list[str]:
    """Valida e guarda IPs de guardas (só IPs públicos literais)."""
    global _GUARDS_V4, _GUARDS_V6
    v4, v6 = [], []
    for raw in (ips or []):
        try:
            ip = ipaddress.ip_address(str(raw).strip().strip("[]"))
        except ValueError:
            continue
        if not ip.is_global:
            continue
        (v4 if ip.version == 4 else v6).append(str(ip))
    _GUARDS_V4, _GUARDS_V6 = sorted(set(v4)), sorted(set(v6))
    return _GUARDS_V4 + _GUARDS_V6


def build_nft_script(v4: list[str], v6: list[str]) -> str:
    """Monta o script nft (puro/testável). Política: OUTPUT drop, só o
    essencial passa (loopback, estabelecidas, DHCP, TCP p/ guardas)."""
    e4 = ", ".join(v4) if v4 else "255.255.255.254"
    e6 = ", ".join(v6) if v6 else "::ffff:255.255.255.254"
    return f"""add table inet {TABLE}
add set inet {TABLE} tor_guards {{ type ipv4_addr; flags interval; elements = {{ {e4} }} }}
add set inet {TABLE} tor6_guards {{ type ipv6_addr; flags interval; elements = {{ {e6} }} }}
add chain inet {TABLE} output {{ type filter hook output priority 0; policy drop; }}
add rule inet {TABLE} output iif "lo" accept
add rule inet {TABLE} output ct state established,related accept
add rule inet {TABLE} output udp dport 67 ip daddr 255.255.255.255 accept
add rule inet {TABLE} output ip daddr @tor_guards meta l4proto tcp accept
add rule inet {TABLE} output ip6 daddr @tor6_guards meta l4proto tcp accept
"""


def _nft_admin(args: list[str]) -> tuple[bool, str]:
    """nft com root: direto se euid==0, senão via pkexec."""
    try:
        if os.geteuid() == 0:
            return _run(["nft"] + args, timeout=60)
    except AttributeError:
        pass
    if _have("pkexec"):
        return _run(["pkexec", "nft"] + args, timeout=60)
    return False, "sem root (rode como root ou instale policykit-1 p/ pkexec)"


def _pkexec_nft(script: str) -> None:
    if not _have("nft"):
        raise RuntimeError("nftables ausente: sudo apt install nftables")
    fd, path = tempfile.mkstemp(prefix="anonshield-nft-", suffix=".nft")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(script)
        os.chmod(path, 0o600)
        ok, out = _nft_admin(["-f", path])
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    if not ok:
        raise RuntimeError((out or "nft falhou")[:300])


def firewall_block() -> None:
    # Apaga resto anterior (ignora "não existe") e aplica do zero.
    _nft_admin(["delete", "table", "inet", TABLE])
    _pkexec_nft(build_nft_script(_GUARDS_V4, _GUARDS_V6))


def refresh_linux_guards() -> bool:
    """Reaplica só os sets de guardas (sem reconstruir a tabela)."""
    if not _have("nft"):
        return False
    for fam, name, ips in (("ip", "tor_guards", _GUARDS_V4),
                           ("ip6", "tor6_guards", _GUARDS_V6)):
        _nft_admin(["flush", "set", "inet", TABLE, name])
        if ips:
            _nft_admin(["add", "element", "inet", TABLE, name,
                        "{ " + ", ".join(ips) + " }"])
    return True


def firewall_active() -> bool:
    if not _have("nft"):
        return False
    ok, _ = _run(["nft", "list", "table", "inet", TABLE], timeout=15)
    return ok


def firewall_unblock() -> None:
    if not _have("nft"):
        return
    _nft_admin(["delete", "table", "inet", TABLE])


# ---------- sondas POSIX ----------

VPN_POSIX = {
    "nordvpn": "NordVPN", "expressvpn": "ExpressVPN", "protonvpn": "ProtonVPN",
    "mullvad-vpn": "Mullvad", "surfshark": "Surfshark", "openvpn": "OpenVPN",
    "wireguard": "WireGuard", "wg": "WireGuard",
}


def vpn_running() -> list[dict]:
    ok, out = _run(["pgrep", "-a", "-f",
                    "openvpn|wireguard|nordvpn|expressvpn|protonvpn|mullvad|surfshark"],
                   timeout=15)
    if not ok:
        return []
    found: dict[str, None] = {}
    for line in (out or "").splitlines():
        low = line.lower()
        for proc, name in VPN_POSIX.items():
            if proc in low and "pgrep" not in low:
                found[name] = None
    exe = shutil.which("openvpn") or ""
    return [{"name": n, "exe": exe if n == "OpenVPN" else ""} for n in sorted(found)]


def system_dns() -> str:
    try:
        with open("/etc/resolv.conf", encoding="utf-8", errors="replace") as f:
            import re as _re
            for line in f:
                m = _re.match(r"\s*nameserver\s+(\d+\.\d+\.\d+\.\d+)", line)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return ""


def socks_live(ports: list[int]) -> list[dict]:
    """Conexões no(s) SOCKS via `ss` (só leitura)."""
    out: list[dict] = []
    try:
        import re as _re
        wanted = {int(p) for p in (ports or [])}
        if not wanted or not _have("ss"):
            return out
        ok, txt = _run(["ss", "-tnp"], timeout=20)
        if not ok:
            return out
        hits: dict[int, set] = {}
        for line in (txt or "").splitlines():
            parts = line.split()
            if len(parts) < 6 or parts[0] != "ESTAB":
                continue
            try:
                lp = int(parts[3].rsplit(":", 1)[-1])
                rp = int(parts[4].rsplit(":", 1)[-1])
                m = _re.search(r"users:\(\(\"([^\"]+)\",pid=(\d+)", line)
                if not m:
                    continue
                name, pid = m.group(1), int(m.group(2))
            except (ValueError, IndexError):
                continue
            use = lp if lp in wanted else (rp if rp in wanted else 0)
            if use:
                hits.setdefault((pid, name), set()).add(use)
        for (pid, name), ps in sorted(hits.items()):
            out.append({"pid": pid, "name": name, "ports": sorted(ps)})
    except Exception:
        pass
    return out
