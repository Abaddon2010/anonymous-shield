# Copyright (C) 2026 Abaddon2010
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later
# Licenca dupla: Apache-2.0 OU GPL-3.0-ou-posterior, a sua escolha. Ver LICENSE-APACHE e LICENSE na raiz.

"""Anonymous Shield — usuários locais (opcional).

- Nomes de usuário criptografados (AES-256-GCM, chave do dispositivo).
- Senha verificada por PBKDF2 (nunca armazenada).
- Cada usuário tem seu próprio cofre (`users/<id>/config.enc`).
- Convidado = sem senha (config.json em texto em `app_dirs()`).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid

from . import vault as _vault

ITERS = 600_000
# NÃO RENOMEAR: este pepper protege cofres já criados; mudá-lo
# invalidaria os perfis existentes.
_PEPPER = b"torshield-local-users-v1"


def _meta_path() -> str:
    from .config import app_dirs
    cfg, _ = app_dirs()
    return os.path.join(cfg, "users.meta")


def _device_secret() -> bytes:
    """Segredo estável da máquina (só ofuscação local, sem dados pessoais).

    LIMITAÇÃO DOCUMENTADA: o MachineGuid é legível por qualquer processo
    local, então isto NÃO resiste a atacante com acesso à máquina — serve
    só p/ não expor nomes em texto puro. As SENHAS continuam protegidas
    por PBKDF2-600k (nunca armazenadas). Endurecer no futuro: DPAPI
    (CryptProtectData) via ctypes.
    """
    machine = ""
    try:
        import subprocess as _sp
        p = _sp.run(
            ["reg", "query", r"HKLM\SOFTWARE\Microsoft\Cryptography", "/v", "MachineGuid"],
            capture_output=True, text=True, timeout=10,
            creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0))
        for line in (p.stdout or "").splitlines():
            if "MachineGuid" in line:
                parts = line.split()
                if len(parts) >= 3:
                    machine = parts[-1].strip("{} \t")
    except Exception:
        machine = ""
    if not machine and os.name != "nt":
        for cand in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            try:
                with open(cand, encoding="utf-8") as f:
                    machine = f.read().strip()
                    break
            except OSError:
                pass
    seed = (machine or "fallback") + "|anonshield-users"
    return hashlib.pbkdf2_hmac("sha256", seed.encode(), _PEPPER, 100_000, dklen=32)


def _load_meta() -> dict:
    path = _meta_path()
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict) and isinstance(raw.get("users"), list):
            return raw
    except (OSError, ValueError):
        pass
    return {"users": []}


def _save_meta(meta: dict) -> None:
    path = _meta_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def _enc_name(name: str) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = secrets.token_bytes(12)
    ct = AESGCM(_device_secret()).encrypt(nonce, name.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode()


def _dec_name(blob: str) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    raw = base64.b64decode(blob)
    return AESGCM(_device_secret()).decrypt(raw[:12], raw[12:], None).decode("utf-8")


def _hash_pw(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERS, dklen=32)


def list_users() -> list[dict]:
    """[{id, name}] — ignora registros ilegíveis."""
    out = []
    for u in _load_meta().get("users", []):
        try:
            out.append({"id": u["id"], "name": _dec_name(u["name_ct"])})
        except Exception:
            continue
    return out


def user_dir(uid: str) -> str:
    from .config import app_dirs
    cfg, _ = app_dirs()
    return os.path.join(cfg, "users", uid)


def create_user(username: str, password: str) -> str:
    """Cria usuário + cofre próprio. Retorna id. Erros em ValueError."""
    username = (username or "").strip()
    if not username:
        raise ValueError("empty")
    if len(password) < 8:
        raise ValueError("short")
    for u in list_users():
        if u["name"].lower() == username.lower():
            raise ValueError("exists")
    uid = uuid.uuid4().hex[:16]
    salt = secrets.token_bytes(16)
    rec = {
        "id": uid,
        "name_ct": _enc_name(username),
        "salt": base64.b64encode(salt).decode(),
        "iters": ITERS,
        "hash": base64.b64encode(_hash_pw(password, salt)).decode(),
    }
    meta = _load_meta()
    meta["users"].append(rec)
    _save_meta(meta)
    # Cofre próprio com config padrão.
    udir = user_dir(uid)
    os.makedirs(udir, exist_ok=True)
    from .config import AppConfig
    cfg = AppConfig()
    cfg.password = password
    _vault.encrypt_obj(cfg.to_dict(), password, udir)
    return uid


def is_locked(uid: str) -> float:
    """Segundos restantes de bloqueio (0 = não bloqueado)."""
    for u in _load_meta().get("users", []):
        if u.get("id") == uid:
            try:
                rem = float(u.get("locked_until", 0) or 0) - time.time()
            except (TypeError, ValueError):
                return 0.0
            return rem if rem > 0 else 0.0
    return 0.0


def verify_user(uid: str, password: str) -> bool:
    if is_locked(uid) > 0:
        return False
    for u in _load_meta().get("users", []):
        if u.get("id") == uid:
            try:
                salt = base64.b64decode(u["salt"])
                expect = base64.b64decode(u["hash"])
            except (ValueError, KeyError):
                return False
            return hmac.compare_digest(_hash_pw(password, salt), expect)
    return False


MAX_FAILS = 3


def reset_fails(uid: str) -> None:
    meta = _load_meta()
    for u in meta.get("users", []):
        if u.get("id") == uid and (u.get("fails") or u.get("locked_until")):
            u["fails"] = 0
            u.pop("locked_until", None)
            _save_meta(meta)
            return


def register_fail(uid: str) -> tuple[bool, int]:
    """Registra erro de senha. Retorna (apagado, restantes).

    Regra anti-força-bruta (vale p/ TODOS os usuários): no 3º erro
    seguido o perfil é BLOQUEADO por 5 min (`locked_until`) — o
    perfil + cofre NÃO são mais apagados. O valor `True` (apagado)
    é mantido só por compatibilidade legada e não deve mais ocorrer.
    Contador persiste em users.meta (reiniciar não zera).
    """
    meta = _load_meta()
    for u in meta.get("users", []):
        if u.get("id") == uid:
            if is_locked(uid) > 0:
                return False, 0
            fails = int(u.get("fails", 0) or 0) + 1
            u["fails"] = fails
            if fails >= MAX_FAILS:
                u["locked_until"] = time.time() + 300
                _save_meta(meta)
                return False, 0
            _save_meta(meta)
            return False, MAX_FAILS - fails
    return False, MAX_FAILS


def delete_user_force(uid: str) -> bool:
    """Apaga conta + cofre SEM pedir senha (uso interno: wipe anti-brute)."""
    meta = _load_meta()
    if not any(u.get("id") == uid for u in meta.get("users", [])):
        return False
    meta["users"] = [u for u in meta.get("users", []) if u.get("id") != uid]
    _save_meta(meta)
    udir = user_dir(uid)
    for name in ("config.enc", "vault.meta", "config.json"):
        _vault.shred(os.path.join(udir, name))
    try:
        os.rmdir(udir)
    except OSError:
        pass
    return True


def delete_user(uid: str, password: str) -> bool:
    """Remove conta + cofre (exige senha)."""
    if not verify_user(uid, password):
        return False
    meta = _load_meta()
    meta["users"] = [u for u in meta.get("users", []) if u.get("id") != uid]
    _save_meta(meta)
    udir = user_dir(uid)
    for name in ("config.enc", "vault.meta", "config.json"):
        _vault.shred(os.path.join(udir, name))
    try:
        os.rmdir(udir)
    except OSError:
        pass
    return True
