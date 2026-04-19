"""Unit tests for DiscountRuleRegistry."""
from decimal import Decimal

import pytest

from plugins.discount.discount.interfaces import DiscountContext, DiscountScope, IDiscountRule
from plugins.discount.discount.registry import DiscountRuleRegistry


class FakeShopRule(IDiscountRule):
    def can_apply(self, line_item_type, line_item_extra_data, discount_scope):
        return line_item_extra_data.get("plugin") == "shop"

    def evaluate(
        self, line_item_type, line_item_extra_data, unit_price, quantity, discount_type, discount_value, context
    ):
        total = unit_price * quantity
        if discount_type == "PERCENTAGE":
            return (total * discount_value / Decimal("100")).quantize(Decimal("0.01"))
        return Decimal("0")

    def get_supported_scopes(self):
        return [DiscountScope.ECOMMERCE]


class FakeSubscriptionRule(IDiscountRule):
    def can_apply(self, line_item_type, line_item_extra_data, discount_scope):
        return line_item_type == "SUBSCRIPTION"

    def evaluate(
        self, line_item_type, line_item_extra_data, unit_price, quantity, discount_type, discount_value, context
    ):
        total = unit_price * quantity
        if discount_type == "PERCENTAGE":
            return (total * discount_value / Decimal("100")).quantize(Decimal("0.01"))
        return Decimal("0")

    def get_supported_scopes(self):
        return [DiscountScope.SUBSCRIPTION]


@pytest.fixture
def registry():
    return DiscountRuleRegistry()


@pytest.fixture
def context():
    return DiscountContext(
        user_id=None,
        invoice_id=None,
        coupon_code=None,
        cart_total=Decimal("100.00"),
        line_item_count=2,
    )


def test_register_rule(registry):
    rule = FakeShopRule()
    registry.register(rule)
    assert registry.rule_count == 1


def test_get_rules_for_scope(registry):
    shop_rule = FakeShopRule()
    subscription_rule = FakeSubscriptionRule()
    registry.register(shop_rule)
    registry.register(subscription_rule)

    shop_rules = registry.get_rules_for_scope(DiscountScope.ECOMMERCE)
    assert len(shop_rules) == 1
    assert shop_rules[0] is shop_rule

    subscription_rules = registry.get_rules_for_scope(DiscountScope.SUBSCRIPTION)
    assert len(subscription_rules) == 1
    assert subscription_rules[0] is subscription_rule


def test_evaluate_ecommerce_percentage(registry, context):
    registry.register(FakeShopRule())

    amount = registry.evaluate_discount(
        line_item_type="CUSTOM",
        line_item_extra_data={"plugin": "shop"},
        unit_price=Decimal("50.00"),
        quantity=2,
        discount_id="test",
        discount_type="PERCENTAGE",
        discount_value=Decimal("20"),
        discount_scope=DiscountScope.ECOMMERCE,
        context=context,
    )
    assert amount == Decimal("20.00")


def test_evaluate_no_matching_rule_returns_zero(registry, context):
    registry.register(FakeShopRule())

    amount = registry.evaluate_discount(
        line_item_type="SUBSCRIPTION",
        line_item_extra_data={"plugin": "subscription"},
        unit_price=Decimal("50.00"),
        quantity=1,
        discount_id="test",
        discount_type="PERCENTAGE",
        discount_value=Decimal("20"),
        discount_scope=DiscountScope.SUBSCRIPTION,
        context=context,
    )
    assert amount == Decimal("0")


def test_global_scope_uses_default_calculation(registry, context):
    amount = registry.evaluate_discount(
        line_item_type="CUSTOM",
        line_item_extra_data={},
        unit_price=Decimal("100.00"),
        quantity=1,
        discount_id="test",
        discount_type="PERCENTAGE",
        discount_value=Decimal("15"),
        discount_scope=DiscountScope.GLOBAL,
        context=context,
    )
    assert amount == Decimal("15.00")


def test_global_fixed_amount(registry, context):
    amount = registry.evaluate_discount(
        line_item_type="CUSTOM",
        line_item_extra_data={},
        unit_price=Decimal("30.00"),
        quantity=1,
        discount_id="test",
        discount_type="FIXED_AMOUNT",
        discount_value=Decimal("5.00"),
        discount_scope=DiscountScope.GLOBAL,
        context=context,
    )
    assert amount == Decimal("5.00")


def test_fixed_amount_capped_at_total(registry, context):
    amount = registry.evaluate_discount(
        line_item_type="CUSTOM",
        line_item_extra_data={},
        unit_price=Decimal("3.00"),
        quantity=1,
        discount_id="test",
        discount_type="FIXED_AMOUNT",
        discount_value=Decimal("50.00"),
        discount_scope=DiscountScope.GLOBAL,
        context=context,
    )
    assert amount == Decimal("3.00")


def test_unregister_rule(registry):
    rule = FakeShopRule()
    registry.register(rule)
    assert registry.rule_count == 1
    registry.unregister(rule)
    assert registry.rule_count == 0
