import base64
import io
from typing import Optional

import pyotp
import qrcode

from config import settings


class TOTPManager:
    @staticmethod
    def generate_secret() -> str:
        return pyotp.random_base32()

    @staticmethod
    def get_provisioning_uri(secret: str, username: str) -> str:
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=username, issuer_name=settings.TOTP_ISSUER)

    @staticmethod
    def get_qr_code_b64(provisioning_uri: str) -> str:
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    @staticmethod
    def verify(secret: str, code: str, valid_window: int = 1) -> bool:
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=valid_window)

    @staticmethod
    def generate_backup_codes(count: int = 10) -> list[str]:
        import secrets
        return [secrets.token_hex(8).upper() for _ in range(count)]
