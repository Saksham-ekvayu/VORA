"""Mirrors `helper.js#generateTempPassword` from profile-service-main."""

import random

_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_LOWER = "abcdefghijklmnopqrstuvwxyz"
_DIGITS = "0123456789"
_SPECIALS = "@$!%*#?&"
_ALL = _UPPER + _LOWER + _DIGITS + _SPECIALS


def generate_temp_password(length: int = 12) -> str:
    chars = [
        random.choice(_UPPER),
        random.choice(_LOWER),
        random.choice(_DIGITS),
        random.choice(_SPECIALS),
    ]
    chars += [random.choice(_ALL) for _ in range(max(0, length - len(chars)))]
    random.shuffle(chars)
    return "".join(chars)
