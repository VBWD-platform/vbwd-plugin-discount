"""Integration: populate_db seeds the discount/coupon catalog on install.

Proves the e2e specs can rely on seeded codes with zero manual setup, and that
re-running the seeder creates nothing new (idempotent — safe on every deploy).
"""
from plugins.discount.populate_db import populate
from plugins.discount.discount.models.coupon import Coupon
from plugins.discount.discount.models.discount import DiscountRule

_EXPECTED_CODES = {"SUMMER2026", "WELCOME5", "FREESHIP", "SUB30", "EARLYBIRD"}

# The schema (incl. the optional email-template table) is built once in the
# session ``app`` fixture; each test below runs inside the conftest ``db``
# fixture's rolled-back transaction, so the seeded rows never persist.


def test_populate_seeds_five_discounts_and_coupons(db):
    populate()

    assert db.session.query(DiscountRule).count() == 5
    assert db.session.query(Coupon).count() == 5
    codes = {c.code for c in db.session.query(Coupon).all()}
    assert _EXPECTED_CODES <= codes


def test_populate_is_idempotent(db):
    populate()
    populate()

    assert db.session.query(DiscountRule).count() == 5
    assert db.session.query(Coupon).count() == 5
