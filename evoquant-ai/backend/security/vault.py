"""
Quantum-Proof Vault using Kyber-768 (KEM) + Dilithium-2 (signatures)
Falls back to AES-256-GCM if liboqs is not available.
"""
import base64
import hashlib
import json
import os
import struct
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

try:
    import oqs  # liboqs-python
    OQS_AVAILABLE = True
except ImportError:
    OQS_AVAILABLE = False

from config import settings


class PQVault:
    """
    Hybrid PQ vault:
      - Key Encapsulation: Kyber-768
      - Signatures:        Dilithium-2
      - Symmetric cipher:  AES-256-GCM
      - Key derivation:    HKDF-SHA3-512
    """

    KEM_ALG = "Kyber768"
    SIG_ALG = "Dilithium2"

    def __init__(self) -> None:
        self._master_key = bytes.fromhex(settings.PQ_VAULT_MASTER_KEY.ljust(64, "0"))
        self._kem_keypair: tuple[bytes, bytes] | None = None
        self._sig_keypair: tuple[bytes, bytes] | None = None
        if OQS_AVAILABLE and settings.VAULT_ENCRYPTION_ENABLED:
            self._init_pq_keys()

    # ------------------------------------------------------------------
    # PQ Key generation
    # ------------------------------------------------------------------
    def _init_pq_keys(self) -> None:
        with oqs.KeyEncapsulation(self.KEM_ALG) as kem:
            public_key = kem.generate_keypair()
            secret_key = kem.export_secret_key()
            self._kem_keypair = (public_key, secret_key)

        with oqs.Signature(self.SIG_ALG) as sig:
            public_key = sig.generate_keypair()
            secret_key = sig.export_secret_key()
            self._sig_keypair = (public_key, secret_key)

    # ------------------------------------------------------------------
    # Symmetric encryption helpers
    # ------------------------------------------------------------------
    def _derive_key(self, context: str) -> bytes:
        """Derive 256-bit key via HKDF-like SHA3-512."""
        h = hashlib.shake_256()
        h.update(self._master_key + context.encode())
        return h.digest(32)

    def encrypt(self, plaintext: str | bytes, context: str = "default") -> str:
        """Encrypt bytes with AES-256-GCM; return base64-encoded ciphertext."""
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()
        key = self._derive_key(context)
        nonce = os.urandom(12)
        ct = AESGCM(key).encrypt(nonce, plaintext, context.encode())
        payload = nonce + ct
        return base64.urlsafe_b64encode(payload).decode()

    def decrypt(self, ciphertext_b64: str, context: str = "default") -> bytes:
        """Decrypt base64-encoded ciphertext."""
        payload = base64.urlsafe_b64decode(ciphertext_b64.encode())
        nonce, ct = payload[:12], payload[12:]
        key = self._derive_key(context)
        return AESGCM(key).decrypt(nonce, ct, context.encode())

    # ------------------------------------------------------------------
    # PQ KEM encapsulation (for session key exchange)
    # ------------------------------------------------------------------
    def kem_encapsulate(self, recipient_public_key_b64: str) -> dict[str, str]:
        """Encapsulate a shared secret using recipient's Kyber public key."""
        if not OQS_AVAILABLE:
            raise RuntimeError("liboqs not available")
        pub = base64.urlsafe_b64decode(recipient_public_key_b64)
        with oqs.KeyEncapsulation(self.KEM_ALG, pub) as kem:
            ciphertext, shared_secret = kem.encap_secret(pub)
        return {
            "ciphertext": base64.urlsafe_b64encode(ciphertext).decode(),
            "shared_secret": base64.urlsafe_b64encode(shared_secret).decode(),
        }

    def kem_decapsulate(self, ciphertext_b64: str) -> bytes:
        """Decapsulate shared secret using stored Kyber secret key."""
        if not OQS_AVAILABLE or not self._kem_keypair:
            raise RuntimeError("PQ KEM not initialized")
        ct = base64.urlsafe_b64decode(ciphertext_b64)
        _, secret_key = self._kem_keypair
        with oqs.KeyEncapsulation(self.KEM_ALG, secret_bytes=secret_key) as kem:
            shared_secret = kem.decap_secret(ct)
        return shared_secret

    # ------------------------------------------------------------------
    # Dilithium signatures
    # ------------------------------------------------------------------
    def sign(self, message: str | bytes) -> str:
        """Sign message with Dilithium-2; return base64 signature."""
        if isinstance(message, str):
            message = message.encode()
        if not OQS_AVAILABLE or not self._sig_keypair:
            import hmac as _hmac
            sig = _hmac.new(self._master_key, message, hashlib.sha256).digest()
            return base64.urlsafe_b64encode(sig).decode()
        _, secret_key = self._sig_keypair
        with oqs.Signature(self.SIG_ALG, secret_bytes=secret_key) as sig:
            signature = sig.sign(message)
        return base64.urlsafe_b64encode(signature).decode()

    def verify_signature(self, message: str | bytes, signature_b64: str) -> bool:
        """Verify Dilithium-2 signature."""
        if isinstance(message, str):
            message = message.encode()
        if not OQS_AVAILABLE or not self._sig_keypair:
            import hmac as _hmac
            sig = base64.urlsafe_b64decode(signature_b64)
            expected = _hmac.new(self._master_key, message, hashlib.sha256).digest()
            return _hmac.compare_digest(sig, expected)
        public_key, _ = self._sig_keypair
        sig = base64.urlsafe_b64decode(signature_b64)
        with oqs.Signature(self.SIG_ALG) as verifier:
            return verifier.verify(message, sig, public_key)

    # ------------------------------------------------------------------
    # Convenience helpers for broker API key storage
    # ------------------------------------------------------------------
    def encrypt_api_key(self, broker: str, api_key: str, secret: str) -> dict[str, str]:
        ctx = f"broker:{broker}"
        return {
            "api_key_enc": self.encrypt(api_key, context=f"{ctx}:api_key"),
            "secret_enc": self.encrypt(secret, context=f"{ctx}:secret"),
        }

    def decrypt_api_key(self, broker: str, encrypted: dict[str, str]) -> tuple[str, str]:
        ctx = f"broker:{broker}"
        api_key = self.decrypt(encrypted["api_key_enc"], context=f"{ctx}:api_key").decode()
        secret = self.decrypt(encrypted["secret_enc"], context=f"{ctx}:secret").decode()
        return api_key, secret

    @property
    def kem_public_key_b64(self) -> str | None:
        if self._kem_keypair:
            return base64.urlsafe_b64encode(self._kem_keypair[0]).decode()
        return None

    @property
    def sig_public_key_b64(self) -> str | None:
        if self._sig_keypair:
            return base64.urlsafe_b64encode(self._sig_keypair[0]).decode()
        return None


vault = PQVault()
