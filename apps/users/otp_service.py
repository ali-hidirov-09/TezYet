import random
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

OTP_EXPIRE_SECONDS = 120
OTP_RESEND_COOLDOWN = 60


def _otp_key(phone: str) -> str:
    return f"otp:{phone}"


def _cooldown_key(phone: str) -> str:
    return f"otp_cooldown:{phone}"


def generate_otp(phone: str) -> str | None:
    """
    Telefon raqami uchun yangi OTP yaratadi va Redis ga saqlaydi.
    Agar cooldown davomida qayta so'rov kelsa None qaytaradi.
    """
    if cache.get(_cooldown_key(phone)):
        return None

    code = str(random.randint(100000, 999999))
    cache.set(_otp_key(phone), code, timeout=OTP_EXPIRE_SECONDS)
    cache.set(_cooldown_key(phone), True, timeout=OTP_RESEND_COOLDOWN)

    logger.info(f"OTP generated for {phone}")
    return code


def verify_otp(phone: str, code: str) -> bool:
    """
    Foydalanuvchi kiritgan kodni Redis dagi bilan solishtiradi.
    To'g'ri bo'lsa kodni o'chiradi (bir marta ishlatish).
    """
    saved_code = cache.get(_otp_key(phone))

    if saved_code is None:
        return False  # Muddati o'tgan yoki mavjud emas

    if saved_code != code:
        return False

    cache.delete(_otp_key(phone))
    cache.delete(_cooldown_key(phone))
    return True


def get_remaining_seconds(phone: str) -> int:
    """Foydalanuvchiga qancha vaqt qolganini qaytaradi."""
    ttl = cache.ttl(_cooldown_key(phone))
    return max(ttl, 0)
