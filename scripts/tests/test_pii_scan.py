"""Negative control for the PII gate: prove the scanner flags planted PII.

A PII scan that reports zero findings is only evidence if it is known to find
PII when present. Values below are well-known test numbers, not real data.
"""

import pytest

from scripts.pii_scan import build_analyzer, scan_text


@pytest.fixture(scope="module")
def analyzer():
    return build_analyzer()


def test_detects_credit_card_and_email(analyzer):
    text = "Applicant paid with card 4111 1111 1111 1111 and wrote from jane.doe@gmail.com."
    found = {h["entity"] for h in scan_text(analyzer, text, 0.6)}
    assert {"CREDIT_CARD", "EMAIL_ADDRESS"} <= found


def test_policy_prose_is_clean(analyzer):
    text = "A household is eligible when its gross annual income is at or below 50 percent of the area median income."
    assert scan_text(analyzer, text, 0.6) == []
