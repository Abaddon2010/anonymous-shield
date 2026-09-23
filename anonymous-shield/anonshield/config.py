# Copyright (C) 2026 Abaddon2010
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later
# Licenca dupla: Apache-2.0 OU GPL-3.0-ou-posterior, a sua escolha. Ver LICENSE-APACHE e LICENSE na raiz.

"""Anonymous Shield — configuração persistente (JSON, sem dados pessoais)."""
from __future__ import annotations

import json
import locale
import os
from dataclasses import asdict, dataclass, field

from . import vault as _vault

# Repositório oficial de updates (campo travado na UI; diverge → volta sozinho).
UPDATE_REPO_OFFICIAL = "Abaddon2010/anonymous-shield"

# Override da pasta de dados (usuário local logado). None = padrão do SO.
_DATA_OVERRIDE: str | None = None


def set_data_dir(path: str | None) -> None:
    """Fixa a base de config+dados (ex.: pasta do usuário logado)."""
    global _DATA_OVERRIDE
    _DATA_OVERRIDE = path


def detect_lang() -> str:
    from .i18n import _LANG_CODES

    def match(v: str) -> str | None:
        v = (v or "").lower().replace("_", "-")
        if not v:
            return None
        if v in _LANG_CODES:
            return v
        base = v.split("-")[0].split(".")[0]
        if base == "pt":
            return "pt-BR"
        if base in _LANG_CODES:
            return base
        if base == "zh":
            return "zh-CN" if "hans" in v or "cn" in v or "sg" in v else "zh-CN"
        return None

    for key in ("LC_ALL", "LANG", "LANGUAGE", "LANGUAGELIST"):
        hit = match(os.environ.get(key, "").split(".")[0])
        if hit:
            return hit
    try:
        loc = locale.getlocale()[0] or ""
        hit = match(loc)
        if hit:
            return hit
    except Exception:
        pass
    return "pt-BR"


def _migrate_dir(old: str, new: str) -> None:
    """Migração TorShield→Anonymous Shield (1ª execução): move a pasta antiga."""
    try:
        if old != new and os.path.isdir(old) and not os.path.exists(new):
            os.makedirs(os.path.dirname(new), exist_ok=True)
            import shutil as _sh
            _sh.move(old, new)
    except Exception:
        pass


def app_dirs() -> tuple[str, str]:
    """(config_dir, data_dir) — pastas padrão do SO (ou override por usuário)."""
    if _DATA_OVERRIDE:
        cfg = os.path.join(_DATA_OVERRIDE, "cfg")
        data = os.path.join(_DATA_OVERRIDE, "data")
        os.makedirs(cfg, exist_ok=True)
        os.makedirs(data, exist_ok=True)
        return cfg, data
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        cfg = os.path.join(base, "anonshield", "Anonymous Shield")
        local = os.environ.get("LOCALAPPDATA", base)
        data = os.path.join(local, "anonshield", "Anonymous Shield")
        _migrate_dir(os.path.join(base, "torshield", "TorShield"), cfg)
        _migrate_dir(os.path.join(local, "torshield", "TorShield"), data)
    else:
        home = os.path.expanduser("~")
        cfg = os.path.join(home, ".config", "anonshield")
        data = os.path.join(home, ".local", "share", "anonshield")
        _migrate_dir(os.path.join(home, ".config", "torshield"), cfg)
        _migrate_dir(os.path.join(home, ".local", "share", "torshield"), data)
    os.makedirs(cfg, exist_ok=True)
    os.makedirs(data, exist_ok=True)
    return cfg, data


def _fix_legacy_paths(obj: "AppConfig") -> "AppConfig":
    """Apaga caminhos salvos da era TorShield (pasta migrada)."""
    try:
        if "torshield" in (obj.tor_data_dir or "").lower():
            obj.tor_data_dir = ""
    except Exception:
        pass
    return obj


@dataclass
class AppEntry:
    name: str = ""
    path: str = ""
    enabled: bool = True
    custom: bool = False


@dataclass
class SysProxy:
    enabled: bool = False
    server: str = ""
    bypass: str = ""


@dataclass
class AppConfig:
    use_tor: bool = True
    auto_connect: bool = False
    auto_connect_explicit: bool = False
    bridges_enabled: bool = False
    bridge_preset: str = "direto"
    bridges: list = field(default_factory=list)
    pt_path: str = ""
    socks_enabled: bool = False
    socks_port: int = 9150
    test_target: str = "check.torproject.org:80"
    upstream_enabled: bool = False
    upstream_proxy_url: str = "socks5://127.0.0.1:1080"
    kill_switch: bool = False
    dnscrypt_enabled: bool = False
    dnscrypt_mode: str = "tor"
    dnscrypt_bin: str = ""
    dnscrypt_port: int = 5353
    dnscrypt_config: str = ""
    dnscrypt_host: str = "example.com"
    lang: str = field(default_factory=detect_lang)
    theme: str = "dark"
    protect_total: bool = False
    prev_proxy: SysProxy | None = None
    firewall_on: bool = False
    apps: list = field(default_factory=list)
    update_repo: str = UPDATE_REPO_OFFICIAL
    # Logs: nunca gravar em disco (só memória volátil). Opt-in.
    never_store_logs: bool = False
    # Saídas Tor: "all" | "five" | "nine" | "fourteen" (fora dos Olhos).
    exit_mode: str = "all"
    # Rotação automática de IP (nova identidade a cada N segundos).
    auto_rotate: bool = False
    rotate_secs: int = 600
    # Agendador (HH:MM; vazio = desligado).
    sched_enabled: bool = False
    sched_on: str = ""
    sched_off: str = ""
    sched_rotate: str = ""
    # Tor Browser (opcional): caminho do firefox.exe do bundle.
    tor_browser_path: str = ""
    # Ordem da sidebar: ["sec:pid", ...]; vazio = padrão (DASH_SECTIONS).
    sidebar_order: list = field(default_factory=list)
    # Pasta de runtime do Tor escolhida (padrão→Local→Temp); vazio = decidir.
    tor_data_dir: str = ""
    # VPN externa (OpenVPN) p/ Tor-sobre-VPN. vpn_pass: SÓ memória,
    # nunca vai ao disco (removido em to_dict + ovpn-auth triturado).
    vpn_bin: str = ""
    vpn_config: str = ""
    vpn_user: str = ""
    vpn_pass: str = field(default="", repr=False, compare=False)
    # Senha mestra (SÓ memória — nunca vai ao disco).
    password: str = field(default="", repr=False, compare=False)

    def to_dict(self) -> dict:
        raw = asdict(self)
        raw.pop("password", None)
        raw.pop("vpn_pass", None)  # segredo: só memória, nunca em disco
        return raw

    @classmethod
    def load_plain(cls) -> "AppConfig":
        """Perfil convidado: lê só config.json em texto, ignora o cofre (sem senha)."""
        path = os.path.join(app_dirs()[0], "config.json")
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError):
            return cls()
        try:
            prev = raw.get("prev_proxy")
            if isinstance(prev, dict):
                raw["prev_proxy"] = SysProxy(**{k: v for k, v in prev.items() if k in ("enabled", "server", "bypass")})
            apps = raw.get("apps")
            if isinstance(apps, list):
                from .sysprotect import portable as _portable

                clean = []
                for a in apps:
                    if isinstance(a, dict):
                        clean.append({"name": str(a.get("name", "")),
                                      "path": _portable(str(a.get("path", ""))),
                                      "enabled": bool(a.get("enabled", True)),
                                      "custom": bool(a.get("custom", False))})
                raw["apps"] = clean
            known = set(cls.__dataclass_fields__) - {"password"}
            obj = cls(**{k: v for k, v in raw.items() if k in known})
            obj.vpn_pass = ""  # expurga segredo legado
            if not obj.auto_connect_explicit:
                obj.auto_connect = False  # padrão: só conecta no clique
            return _fix_legacy_paths(obj)
        except TypeError:
            return cls()

    @classmethod
    def load(cls, password: str = "") -> "AppConfig":
        cfg, _ = app_dirs()
        if _vault.has_vault(cfg):
            if not password:
                raise _vault.VaultError("locked")
            raw = _vault.decrypt_obj(password, cfg)
            known = set(cls.__dataclass_fields__) - {"password"}
            obj = cls(**{k: v for k, v in raw.items() if k in known})
            obj.password = password
            obj.vpn_pass = ""  # expurga segredo legado; digitar 1x por sessão
            if not obj.auto_connect_explicit:
                obj.auto_connect = False  # padrão: só conecta no clique
            return _fix_legacy_paths(obj)
        path = os.path.join(cfg, "config.json")
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError):
            obj = cls()
            obj.password = password
            return obj
        try:
            prev = raw.get("prev_proxy")
            if isinstance(prev, dict):
                raw["prev_proxy"] = SysProxy(**{k: v for k, v in prev.items() if k in ("enabled", "server", "bypass")})
            apps = raw.get("apps")
            if isinstance(apps, list):
                from .sysprotect import portable as _portable

                clean = []
                for a in apps:
                    if isinstance(a, dict):
                        clean.append({"name": str(a.get("name", "")),
                                      "path": _portable(str(a.get("path", ""))),
                                      "enabled": bool(a.get("enabled", True)),
                                      "custom": bool(a.get("custom", False))})
                raw["apps"] = clean
            known = set(cls.__dataclass_fields__) - {"password"}
            obj = cls(**{k: v for k, v in raw.items() if k in known})
            obj.password = password
            obj.vpn_pass = ""  # expurga segredo legado
            if not obj.auto_connect_explicit:
                obj.auto_connect = False  # padrão: só conecta no clique
            return _fix_legacy_paths(obj)
        except TypeError:
            obj = cls()
            obj.password = password
            return obj

    def save(self) -> None:
        cfg, _ = app_dirs()
        if self.password:
            _vault.encrypt_obj(self.to_dict(), self.password, cfg)
        else:
            path = os.path.join(cfg, "config.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
