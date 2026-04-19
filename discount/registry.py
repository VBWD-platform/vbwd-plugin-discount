"""DiscountRuleRegistry — same pattern as LineItemHandlerRegistry."""
import logging
from decimal import Decimal

from plugins.discount.discount.interfaces import (
    DiscountContext,
    DiscountScope,
    IDiscountRule,
)

logger = logging.getLogger(__name__)


class DiscountRuleRegistry:
    """Registry for plugin-provided discount rules.

    Plugins register their IDiscountRule implementations here.
    The DiscountService uses this registry to evaluate all applicable rules.
    """

    def __init__(self) -> None:
        self._rules: list[IDiscountRule] = []

    def register(self, rule: IDiscountRule) -> None:
        """Register a discount rule."""
        self._rules.append(rule)
        scopes = rule.get_supported_scopes()
        logger.info(
            "Registered discount rule %s for scopes %s",
            type(rule).__name__,
            [s.value for s in scopes],
        )

    def unregister(self, rule: IDiscountRule) -> None:
        """Unregister a discount rule."""
        self._rules = [r for r in self._rules if r is not rule]

    def get_rules_for_scope(self, scope: DiscountScope) -> list[IDiscountRule]:
        """Get all rules that support the given scope."""
        return [r for r in self._rules if scope in r.get_supported_scopes()]

    def evaluate_discount(
        self,
        line_item_type: str,
        line_item_extra_data: dict,
        unit_price: Decimal,
        quantity: int,
        discount_id: "str",
        discount_type: str,
        discount_value: Decimal,
        discount_scope: DiscountScope,
        context: DiscountContext,
    ) -> Decimal:
        """Evaluate a discount against a line item using registered rules.

        Returns the discount amount (positive value) or 0 if no rule applies.
        """
        rules = self.get_rules_for_scope(discount_scope)

        for rule in rules:
            if rule.can_apply(line_item_type, line_item_extra_data, discount_scope):
                amount = rule.evaluate(
                    line_item_type=line_item_type,
                    line_item_extra_data=line_item_extra_data,
                    unit_price=unit_price,
                    quantity=quantity,
                    discount_type=discount_type,
                    discount_value=discount_value,
                    context=context,
                )
                if amount > 0:
                    return amount

        # GLOBAL scope: use default calculation if no plugin rule matched
        if discount_scope == DiscountScope.GLOBAL:
            return self._default_calculate(
                unit_price, quantity, discount_type, discount_value
            )

        return Decimal("0")

    @staticmethod
    def _default_calculate(
        unit_price: Decimal,
        quantity: int,
        discount_type: str,
        discount_value: Decimal,
    ) -> Decimal:
        """Default discount calculation for GLOBAL scope."""
        total = unit_price * quantity

        if discount_type == "PERCENTAGE":
            return (total * discount_value / Decimal("100")).quantize(Decimal("0.01"))
        elif discount_type == "FIXED_AMOUNT":
            return min(discount_value, total)
        elif discount_type == "FREE_SHIPPING":
            return Decimal("0")  # Handled separately

        return Decimal("0")

    @property
    def rule_count(self) -> int:
        return len(self._rules)
