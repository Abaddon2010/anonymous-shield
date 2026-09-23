# Copyright (C) 2026 Abaddon2010
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later
# Licenca dupla: Apache-2.0 OU GPL-3.0-ou-posterior, a sua escolha. Ver LICENSE-APACHE e LICENSE na raiz.

"""Anonymous Shield — cofre AES-256-GCM.

Tudo que é sensível em repouso (config.json com senhas de proxy/VPN,
bridges) mora criptografado em ``config.enc``, aberto só com a senha
mestra. KDF: PBKDF2-HMAC-SHA256 600k iterações (stdlib). Cifra:
AES-256-GCM (pacote ``cryptography``). Salt público em ``vault.meta``.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets

ITERS = 600_000
SALT_LEN = 16
NONCE_LEN = 12


class VaultError(Exception):
    """Erro genérico do cofre."""


class BadPassword(VaultError):
    """Senha incorreta (falha no tag GCM)."""


def _derive(password: str, salt: bytes, iters: int = ITERS) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters, dklen=32)


def _meta_path(config_dir: str) -> str:
    return os.path.join(config_dir, "vault.meta")


def _enc_path(config_dir: str) -> str:
    return os.path.join(config_dir, "config.enc")


def _plain_path(config_dir: str) -> str:
    return os.path.join(config_dir, "config.json")


def has_vault(config_dir: str) -> bool:
    return os.path.exists(_enc_path(config_dir)) or os.path.exists(_meta_path(config_dir))


def has_plaintext(config_dir: str) -> bool:
    return os.path.exists(_plain_path(config_dir))


def _load_meta(config_dir: str) -> tuple[bytes, int]:
    try:
        with open(_meta_path(config_dir), encoding="utf-8") as f:
            meta = json.load(f)
        salt = base64.b64decode(meta["salt"])
        iters = int(meta.get("iters", ITERS))
        if len(salt) != SALT_LEN or iters < 100_000:
            raise VaultError("meta")
        return salt, iters
    except (OSError, ValueError, KeyError) as e:
        raise VaultError(f"vault.meta: {e}")


def encrypt_obj(obj: dict, password: str, config_dir: str) -> None:
    """Criptografa dict → config.enc (gera salt novo)."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt = secrets.token_bytes(SALT_LEN)
    key = _derive(password, salt)
    nonce = secrets.token_bytes(NONCE_LEN)
    ct = AESGCM(key).encrypt(nonce, json.dumps(obj, ensure_ascii=False).encode("utf-8"), None)
    blob = {"nonce": base64.b64encode(nonce).decode(), "ct": base64.b64encode(ct).decode()}
    with open(_enc_path(config_dir), "w", encoding="utf-8") as f:
        json.dump(blob, f)
    with open(_meta_path(config_dir), "w", encoding="utf-8") as f:
        json.dump({"salt": base64.b64encode(salt).decode(), "iters": ITERS}, f)
    # Some a plaintext se existir (apaga de verdade).
    shred(_plain_path(config_dir))
    # Limpa chaves da memória (best-effort).
    _wipe(bytearray(key))


def decrypt_obj(password: str, config_dir: str) -> dict:
    """Descriptografa config.enc. Erro → BadPassword."""
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt, iters = _load_meta(config_dir)
    try:
        with open(_enc_path(config_dir), encoding="utf-8") as f:
            blob = json.load(f)
        nonce = base64.b64decode(blob["nonce"])
        ct = base64.b64decode(blob["ct"])
    except (OSError, ValueError, KeyError) as e:
        raise VaultError(f"config.enc: {e}")
    key = _derive(password, salt, iters)
    try:
        raw = AESGCM(key).decrypt(nonce, ct, None)
    except InvalidTag as e:
        raise BadPassword() from e
    finally:
        _wipe(bytearray(key))
    try:
        obj = json.loads(raw.decode("utf-8"))
    except ValueError as e:
        raise VaultError(f"json: {e}")
    finally:
        # Best-effort: solta a referência ao plaintext (str imutável
        # não pode ser zerada; ver _wipe). Não muda a lógica de cripto.
        try:
            del raw
        except (NameError, UnboundLocalError):
            pass
    if not isinstance(obj, dict):
        raise VaultError("formato")
    return obj


def shred(path: str, passes: int = 1) -> None:
    """Sobrescreve e apaga um arquivo."""
    try:
        size = os.path.getsize(path)
    except OSError:
        return
    try:
        with open(path, "r+b") as f:
            for _ in range(max(1, passes)):
                f.seek(0)
                f.write(secrets.token_bytes(min(size, 1 << 20)) * (max(1, size // (1 << 20)) + 1) if size else b"")
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
    except OSError:
        pass
    try:
        os.remove(path)
    except OSError:
        pass


def reset_vault(config_dir: str) -> None:
    """Apaga cofre + config (recuperação de senha esquecida)."""
    for name in ("config.enc", "vault.meta", "config.json"):
        shred(os.path.join(config_dir, name))


def _wipe(buf: bytearray) -> None:
    """Zera um buffer MUTÁVEL (best-effort).

    Limitação honesta: objetos `str`/`bytes` são imutáveis e NÃO podem
    ser limpos — cópias podem permanecer na memória até o GC. Esta
    função limpa apenas buffers mutáveis (bytearray) passados
    explicitamente; segredos em `str` (ex. senhas) não são cobertos.
    """
    for i in range(len(buf)):
        buf[i] = 0
