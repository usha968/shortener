import pytest
from app.codegen import ALPHABET, base62, make_code

K = 2654435761  # odd and not a multiple of 31


def test_length_and_alphabet():
    code = make_code(1, K)
    assert len(code) == 7 and set(code) <= set(ALPHABET)


def test_no_collisions_over_range():
    codes = {make_code(i, K) for i in range(1, 200_001)}
    assert len(codes) == 200_000


def test_deterministic():
    assert make_code(42, K) == make_code(42, K)


def test_rejects_bad_multiplier():
    with pytest.raises(ValueError):
        make_code(1, 62)  # shares factors with 62**7


def test_rejects_out_of_range_id():
    with pytest.raises(OverflowError):
        make_code(62 ** 7, K)


def test_base62_known_values():
    assert base62(61, 1) == "z"
    assert base62(62, 2) == "10"
