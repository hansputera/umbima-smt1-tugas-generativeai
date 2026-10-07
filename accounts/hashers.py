"""Password hasher matching the Node.js format: scrypt$N$r$p$<saltHex>$<hashHex>."""

import hashlib
import hmac
import secrets

import string

from django.contrib.auth.hashers import BasePasswordHasher


def _scrypt(password: str, salt_hex: str, n: int, r: int, p: int) -> bytes:
    # Node passes the hex string itself as the salt, so its UTF-8 bytes
    # (the 32 hex characters) are what scrypt must receive -- not the
    # 16 bytes decoded from hex.
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt_hex.encode("utf-8"),
        n=n,
        r=r,
        p=p,
        dklen=64,
        maxmem=128 * n * r * 2 + 1024 * 1024,
    )


class NodeScryptPasswordHasher(BasePasswordHasher):
    algorithm = "scrypt"

    def encode(self, password, salt=None):
        # Django's make_password passes its own alphanumeric salt here, but
        # the stored format must stay Node-compatible: 16 random bytes as hex.
        salt = secrets.token_hex(16)
        digest = _scrypt(password, salt, 16384, 8, 1).hex()
        return f"scrypt$16384$8$1${salt}${digest}"

    def identify(self, encoded):
        if not isinstance(encoded, str):
            return False
        parts = encoded.split("$")
        if len(parts) != 6 or parts[0] != "scrypt":
            return False
        salt_hex, hash_hex = parts[4], parts[5]
        return (
            len(salt_hex) == 32
            and len(hash_hex) == 128
            and all(c in string.hexdigits for c in salt_hex + hash_hex)
        )

    def verify(self, password, encoded):
        if not self.identify(encoded):
            return False
        _, n_s, r_s, p_s, salt_hex, hash_hex = encoded.split("$")
        try:
            n, r, p = int(n_s), int(r_s), int(p_s)
        except ValueError:
            return False
        try:
            digest = _scrypt(password, salt_hex, n, r, p)
        except (ValueError, MemoryError):
            return False
        return hmac.compare_digest(digest.hex(), hash_hex)

    def safe_summary(self, encoded):
        return {
            "algorithm": self.algorithm,
            "hash_length": len(encoded.split("$")[-1]),
        }

    def must_update(self, encoded):
        return False

    def harden_runtime(self, password, encoded):
        pass
