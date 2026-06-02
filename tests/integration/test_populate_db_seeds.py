"""Integration: populate_db seeds the discount/coupon catalog on install.

Proves the e2e specs can rely on seeded codes with zero manual setup, and that
re-running the seeder creates nothing new (idempotent — safe on every deploy).
"""
import pytest

from plugins.discount.populate_db import populate
from plugins.discount.discount.models.coupon import Coupon
from plugins.discount.discount.models.discount import DiscountRule

_EXPECTED_CODES = {"SUMMER2026", "WELCOME5", "FREESHIP", "SUB30", "EARLYBIRD"}


@pytest.fixture(autouse=True)
def _email_template_table(db):
    # populate() seeds the email-template catalog when the optional email plugin
    # is installed; register its table so create_all() builds it. The email
    # plugin is absent in isolated plugin CI (and populate() guards its import),
    # so tolerate its absence — the discount seeding still runs and is asserted.
    try:
        import plugins.email.src.models.email_template  # noqa: F401
    except ImportError:
        pass

    db.create_all()


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
