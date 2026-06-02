"""Unit: DiscountService.compute_discount_amount — the scope-independent,
whole-cart discount math the checkout adjustment uses.

Pure (no DB / registry): builds DiscountRule value objects and a service with
mock repos, since this method touches neither.
"""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from plugins.discount.discount.models.discount import (
    DiscountRule,
    DiscountType,
)
from plugins.discount.discount.services.discount_service import DiscountService


def _service():
    return DiscountService(
        registry=MagicMock(),
        discount_repo=MagicMock(),
        coupon_repo=MagicMock(),
        usage_repo=MagicMock(),
        application_repo=MagicMock(),
    )


def _rule(discount_type, value, max_discount=None):
    return DiscountRule(
        name="r",
        slug="r",
        discount_type=discount_type,
        value=Decimal(value),
        max_discount_amount=Decimal(max_discount) if max_discount else None,
    )


@pytest.mark.parametrize(
    "dtype,value,subtotal,expected",
    [
        (DiscountType.PERCENTAGE, "30.00", "100.00", "30.00"),
        (DiscountType.PERCENTAGE, "20.00", "49.99", "10.00"),
        (DiscountType.FIXED_AMOUNT, "5.00", "100.00", "5.00"),
        (DiscountType.FREE_SHIPPING, "0.00", "100.00", "0.00"),
        (DiscountType.BUY_X_GET_Y, "1.00", "100.00", "0.00"),
    ],
)
def test_basic_amounts(dtype, value, subtotal, expected):
    amount = _service().compute_discount_amount(_rule(dtype, value), Decimal(subtotal))
    assert amount == Decimal(expected)


def test_percentage_capped_by_max_discount():
    rule = _rule(DiscountType.PERCENTAGE, "50.00", max_discount="20.00")
    assert _service().compute_discount_amount(rule, Decimal("100.00")) == Decimal(
        "20.00"
    )


def test_fixed_never_exceeds_subtotal():
    rule = _rule(DiscountType.FIXED_AMOUNT, "200.00")
    assert _service().compute_discount_amount(rule, Decimal("100.00")) == Decimal(
        "100.00"
    )


def test_zero_or_negative_subtotal_is_zero():
    rule = _rule(DiscountType.PERCENTAGE, "30.00")
    assert _service().compute_discount_amount(rule, Decimal("0")) == Decimal("0")
