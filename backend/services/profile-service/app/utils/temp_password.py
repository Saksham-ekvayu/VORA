"""Mirrors `helper.js#generateTempPassword` from profile-service-main."""

import secrets
import random
import string


def generate_temp_password(length: int = 12) -> str:
    """Generate a cryptographically secure temporary password.
    
    Uses secrets module which is designed for security-sensitive applications.
    """
    # Define character sets
    upper = string.ascii_uppercase
    lower = string.ascii_lowercase
    digits = string.digits
    specials = "@$!%*#?&"
    all_chars = upper + lower + digits + specials
    
    # Ensure at least one character from each category
    chars = [
        secrets.choice(upper),
        secrets.choice(lower),
        secrets.choice(digits),
        secrets.choice(specials),
    ]
    
    # Fill remaining length with random characters from all sets
    chars += [secrets.choice(all_chars) for _ in range(max(0, length - len(chars)))]
    
    # Shuffle securely using SystemRandom (cryptographically secure RNG
    # backed by the OS). Use random.SystemRandom rather than secrets.SystemRandom
    # because secrets does not expose SystemRandom.
    rng = random.SystemRandom()
    rng.shuffle(chars)
    
    return "".join(chars)