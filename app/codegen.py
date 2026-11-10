import math

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def base62(n: int, length: int) -> str:
    chars = []
    while n:
        n, r = divmod(n, 62)
        chars.append(ALPHABET[r])
    return "".join(reversed(chars)).rjust(length, "0")


def make_code(seq_id: int, multiplier: int, length: int = 7) -> str:
    """Bijective scramble of a sequence id: distinct ids give distinct codes."""
    space = 62 ** length
    if math.gcd(multiplier, space) != 1:
        raise ValueError("multiplier must be coprime to 62**length (odd, not a multiple of 31)")
    if not 0 < seq_id < space:
        raise OverflowError("sequence id outside code space")
    return base62((seq_id * multiplier) % space, length)
