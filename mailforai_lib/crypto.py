"""Cifra o histórico antes de publicar.

O site é estático e público — quem tem a URL baixa o arquivo. Então o que
sobe é ciphertext: PBKDF2-SHA256 deriva duas chaves da senha, AES-256-CBC
cifra e HMAC-SHA256 autentica (encrypt-then-MAC). São exatamente as
primitivas que o WebCrypto do navegador implementa, o que deixa a página
decifrar sem biblioteca nenhuma.

AES vem do binário `openssl`, porque a stdlib do Python não traz cifra
simétrica — é a única dependência externa do projeto, e só neste comando.
"""

import base64
import hashlib
import hmac
import json
import os
import shutil
import subprocess
from typing import Any, Dict

ITERATIONS = 250_000
SALT_BYTES = 16
IV_BYTES = 16


class CryptoError(RuntimeError):
    pass


def _openssl() -> str:
    path = shutil.which("openssl")
    if not path:
        raise CryptoError("o comando 'openssl' não está no PATH — necessário para publicar")
    return path


def _derive(passphrase: str, salt: bytes) -> Dict[str, bytes]:
    material = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, ITERATIONS, dklen=64)
    return {"enc": material[:32], "mac": material[32:]}


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


def encrypt(plaintext: str, passphrase: str) -> Dict[str, Any]:
    if len(passphrase) < 8:
        raise CryptoError("a senha do histórico precisa de pelo menos 8 caracteres")
    salt = os.urandom(SALT_BYTES)
    iv = os.urandom(IV_BYTES)
    keys = _derive(passphrase, salt)
    proc = subprocess.run(
        [_openssl(), "enc", "-aes-256-cbc",
         "-K", keys["enc"].hex(), "-iv", iv.hex()],
        input=plaintext.encode(), capture_output=True,
    )
    if proc.returncode != 0:
        raise CryptoError(f"openssl falhou: {proc.stderr.decode().strip()}")
    ciphertext = proc.stdout
    tag = hmac.new(keys["mac"], salt + iv + ciphertext, hashlib.sha256).digest()
    return {
        "v": 1,
        "kdf": {"name": "PBKDF2", "hash": "SHA-256", "iterations": ITERATIONS},
        "cipher": "AES-256-CBC",
        "mac": "HMAC-SHA-256",
        "salt": _b64(salt),
        "iv": _b64(iv),
        "ct": _b64(ciphertext),
        "tag": _b64(tag),
    }


def decrypt(blob: Dict[str, Any], passphrase: str) -> str:
    """Existe para o teste provar que a cifra fecha o ciclo."""
    salt = base64.b64decode(blob["salt"])
    iv = base64.b64decode(blob["iv"])
    ciphertext = base64.b64decode(blob["ct"])
    keys = _derive(passphrase, salt)
    expected = hmac.new(keys["mac"], salt + iv + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, base64.b64decode(blob["tag"])):
        raise CryptoError("senha errada ou arquivo adulterado")
    proc = subprocess.run(
        [_openssl(), "enc", "-d", "-aes-256-cbc",
         "-K", keys["enc"].hex(), "-iv", iv.hex()],
        input=ciphertext, capture_output=True,
    )
    if proc.returncode != 0:
        raise CryptoError(f"openssl falhou: {proc.stderr.decode().strip()}")
    return proc.stdout.decode()


def encrypt_json(data: Any, passphrase: str) -> str:
    return json.dumps(encrypt(json.dumps(data, ensure_ascii=False), passphrase), indent=2)
