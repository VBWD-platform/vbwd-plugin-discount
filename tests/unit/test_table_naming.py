"""Oracle: discount tables must be `discount_`-prefixed (sprint S43.2)."""
from plugins.discount.discount.models.coupon import Coupon
from plugins.discount.discount.models.coupon_usage import CouponUsage
from plugins.discount.discount.models.discount import DiscountRule


def test_discount_tables_are_plugin_prefixed():
    assert Coupon.__tablename__ == "discount_coupon"
    assert CouponUsage.__tablename__ == "discount_coupon_usage"
    assert DiscountRule.__tablename__ == "discount_rule"
    for model in (Coupon, CouponUsage, DiscountRule):
        assert model.__tablename__.startswith("discount_")
