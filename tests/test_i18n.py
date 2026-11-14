"""Tests for the number formatting in trend/i18n.py.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
from trend.i18n import num


def test_values_that_round_to_zero_have_no_sign():
    assert num(-0.00005, "en", 3, signed=True) == "0.000"
    assert num(0.00004, "tr", 3, signed=True) == "0,000"
    assert num(-0.004, "en", 2) == "0.00"


def test_signed_numbers_keep_their_sign_and_decimal_comma():
    assert num(0.326, "en", 2, signed=True) == "+0.33"
    assert num(-1.218, "tr", 2, signed=True) == "-1,22"
    assert num(25.19, "en", 1) == "25.2"
