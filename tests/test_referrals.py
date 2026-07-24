"""Tests for the referral program: store logic and the invite screen."""

from __future__ import annotations

from jarvis.interfaces.bot_menu import referral_link, screen_referral
from jarvis.interfaces.referrals import ReferralStore


def _flat(rows):
    return [data for row in rows for _, data in row]


def test_records_a_referral_once():
    store = ReferralStore(":memory:")
    assert store.record(referrer_id=1, referred_id=2) is True
    # Same person can't be referred twice (even by someone else).
    assert store.record(referrer_id=1, referred_id=2) is False
    assert store.record(referrer_id=9, referred_id=2) is False
    assert store.count(1) == 1
    assert store.referred_by(2) == "1"
    store.close()


def test_rejects_self_referral():
    store = ReferralStore(":memory:")
    assert store.record(referrer_id=5, referred_id=5) is False
    assert store.count(5) == 0
    store.close()


def test_counts_multiple_referrals():
    store = ReferralStore(":memory:")
    for uid in (10, 11, 12):
        assert store.record(referrer_id=1, referred_id=uid) is True
    assert store.count(1) == 3
    assert store.count(2) == 0
    store.close()


def test_referral_link_format():
    assert referral_link("jarvis_bot", 42) == "https://t.me/jarvis_bot?start=ref_42"


def test_screen_referral_shows_link_bonus_and_share():
    text, rows = screen_referral(
        "en", link="https://t.me/jarvis_bot?start=ref_42",
        count=3, bonus_each=20)
    assert "ref_42" in text
    assert "+60" in text            # 3 referrals × 20
    # Share button is a t.me share URL.
    assert any(d.startswith("https://t.me/share/url") for d in _flat(rows))
    assert "m:main" in _flat(rows)  # back
