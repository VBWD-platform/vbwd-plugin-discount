"""DiscountService — orchestrates discount evaluation and coupon validation."""
import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from vbwd.utils.datetime_utils import utcnow

from plugins.discount.discount.interfaces import DiscountContext, DiscountScope
from plugins.discount.discount.models.coupon import Coupon
from plugins.discount.discount.models.coupon_usage import CouponUsage
from plugins.discount.discount.models.discount import DiscountRule
from plugins.discount.discount.models.discount_application import DiscountApplication
from plugins.discount.discount.registry import DiscountRuleRegistry
from plugins.discount.discount.repositories.coupon_repository import CouponRepository
from plugins.discount.discount.repositories.coupon_usage_repository import (
    CouponUsageRepository,
)
from plugins.discount.discount.repositories.discount_application_repository import (
    DiscountApplicationRepository,
)
from plugins.discount.discount.repositories.discount_repository import (
    DiscountRepository,
)

logger = logging.getLogger(__name__)


class CouponValidationError(Exception):
    """Raised when a coupon fails validation."""


class DiscountService:
    """Orchestrates discount evaluation, coupon validation, and usage tracking."""

    def __init__(
        self,
        registry: DiscountRuleRegistry,
        discount_repo: DiscountRepository,
        coupon_repo: CouponRepository,
        usage_repo: CouponUsageRepository,
        application_repo: DiscountApplicationRepository,
    ) -> None:
        self._registry = registry
        self._discount_repo = discount_repo
        self._coupon_repo = coupon_repo
        self._usage_repo = usage_repo
        self._application_repo = application_repo

    def validate_coupon(
        self,
        code: str,
        user_id: Optional[UUID],
        cart_total: Decimal,
    ) -> Coupon:
        """Validate a coupon code. Raises CouponValidationError if invalid."""
        coupon = self._coupon_repo.find_by_code(code.upper())
        if not coupon:
            raise CouponValidationError("Coupon not found")

        if not coupon.is_active:
            raise CouponValidationError("Coupon is inactive")

        now = utcnow()
        if coupon.starts_at and coupon.starts_at > now:
            raise CouponValidationError("Coupon is not yet active")

        if coupon.expires_at and coupon.expires_at < now:
            raise CouponValidationError("Coupon has expired")

        if coupon.max_uses is not None and coupon.current_uses >= coupon.max_uses:
            raise CouponValidationError("Coupon usage limit reached")

        if user_id and coupon.max_uses_per_user is not None:
            user_uses = self._usage_repo.count_by_coupon_and_user(coupon.id, user_id)
            if user_uses >= coupon.max_uses_per_user:
                raise CouponValidationError("You have already used this coupon")

        discount = self._discount_repo.find_by_id(coupon.discount_id)
        if not discount or not discount.is_active:
            raise CouponValidationError("DiscountRule is not available")

        if discount.min_order_amount and cart_total < discount.min_order_amount:
            raise CouponValidationError(
                f"Minimum order amount is {discount.min_order_amount}"
            )

        return coupon

    def calculate_discount(
        self,
        discount: DiscountRule,
        line_item_type: str,
        line_item_extra_data: dict,
        unit_price: Decimal,
        quantity: int,
        context: DiscountContext,
    ) -> Decimal:
        """Calculate the discount amount for a line item."""
        scope = DiscountScope(discount.scope.value)

        amount = self._registry.evaluate_discount(
            line_item_type=line_item_type,
            line_item_extra_data=line_item_extra_data,
            unit_price=unit_price,
            quantity=quantity,
            discount_id=str(discount.id),
            discount_type=discount.discount_type.value,
            discount_value=discount.value,
            discount_scope=scope,
            context=context,
        )

        # Apply max_discount_amount cap
        if discount.max_discount_amount and amount > discount.max_discount_amount:
            amount = discount.max_discount_amount

        return amount

    def compute_discount_amount(
        self,
        discount: DiscountRule,
        subtotal: Decimal,
    ) -> Decimal:
        """Compute the money off a checkout subtotal for a flat (whole-cart)
        discount — the scope-independent path the checkout adjustment uses.

        Unlike :meth:`calculate_discount` (which routes through the per-line
        ``DiscountRuleRegistry`` and only has a default for GLOBAL scope), this
        applies the rule's own ``discount_type`` + ``value`` directly so a
        SUBSCRIPTION/ECOMMERCE coupon reduces the price with no registered rule.
        Only the two cart-reducing types are honoured; FREE_SHIPPING /
        BUY_X_GET_Y are not subtotal reductions (→ 0). Capped at
        ``max_discount_amount`` and never more than the subtotal.
        """
        if subtotal <= 0:
            return Decimal("0")

        discount_type = discount.discount_type.value
        if discount_type == "PERCENTAGE":
            amount = (subtotal * discount.value / Decimal("100")).quantize(
                Decimal("0.01")
            )
        elif discount_type == "FIXED_AMOUNT":
            amount = discount.value
        else:
            return Decimal("0")

        if discount.max_discount_amount and amount > discount.max_discount_amount:
            amount = discount.max_discount_amount
        if amount > subtotal:
            amount = subtotal
        return amount

    def redeem_coupon(
        self,
        coupon: Coupon,
        user_id: UUID,
        invoice_id: Optional[UUID],
        discount_amount: Decimal,
    ) -> CouponUsage:
        """Record coupon usage and increment counters."""
        usage = CouponUsage(
            coupon_id=coupon.id,
            user_id=user_id,
            invoice_id=invoice_id,
            discount_amount=discount_amount,
            used_at=utcnow(),
        )
        self._usage_repo.save(usage)

        coupon.current_uses += 1
        self._coupon_repo.save(coupon)

        discount = self._discount_repo.find_by_id(coupon.discount_id)
        if discount:
            discount.current_uses += 1
            self._discount_repo.save(discount)

        logger.info(
            "Coupon %s redeemed by user %s, discount %.2f",
            coupon.code,
            user_id,
            discount_amount,
        )
        return usage

    def record_application(
        self,
        discount_id: UUID,
        invoice_id: UUID,
        user_id: UUID,
        original_amount: Decimal,
        discount_amount: Decimal,
        line_item_id: Optional[UUID] = None,
        coupon_id: Optional[UUID] = None,
    ) -> DiscountApplication:
        """Create an audit record of a discount application."""
        application = DiscountApplication(
            discount_id=discount_id,
            invoice_id=invoice_id,
            line_item_id=line_item_id,
            user_id=user_id,
            original_amount=original_amount,
            discount_amount=discount_amount,
            final_amount=original_amount - discount_amount,
            coupon_id=coupon_id,
        )
        return self._application_repo.save(application)

    def get_applicable_discounts(
        self,
        scope: Optional[DiscountScope] = None,
    ) -> list[DiscountRule]:
        """Get all active discounts for a scope, checking date range."""
        discounts = self._discount_repo.find_active(scope)
        now = utcnow()
        return [
            discount
            for discount in discounts
            if (not discount.starts_at or discount.starts_at <= now)
            and (not discount.expires_at or discount.expires_at >= now)
            and (discount.max_uses is None or discount.current_uses < discount.max_uses)
        ]
