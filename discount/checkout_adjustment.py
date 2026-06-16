"""The discount plugin's checkout price adjustment.

This is the single bridge from coupon math to the checkout consumers: it
implements the core ``CheckoutPriceAdjustment`` port so subscription/shop
checkouts reduce their subtotal without importing the discount plugin (DIP —
both sides depend only on the core registry). Registered in the plugin's
``on_enable``; the registry is empty when the plugin is disabled, so checkout
degrades to full price (Liskov null-default).
"""
from decimal import Decimal
from uuid import UUID

from vbwd.events.bus import event_bus
from vbwd.extensions import db
from vbwd.services.checkout_price_adjustment_registry import PriceAdjustmentResult

from plugins.discount.discount.models.discount import DiscountScope
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
from plugins.discount.discount.services.discount_service import (
    CouponValidationError,
    DiscountService,
)


def _build_service(session) -> DiscountService:
    return DiscountService(
        registry=DiscountRuleRegistry(),
        discount_repo=DiscountRepository(session),
        coupon_repo=CouponRepository(session),
        usage_repo=CouponUsageRepository(session),
        application_repo=DiscountApplicationRepository(session),
    )


#: The additive redemption event name (S92 B2). Other plugins subscribe to it
#: to react to a coupon redemption; discount only publishes.
COUPON_REDEEMED_EVENT = "discount.coupon_redeemed"


def _publish_coupon_redeemed(
    *, coupon, user_ref, invoice_ref, discount_amount, sale_net_amount
) -> None:
    """Publish ``discount.coupon_redeemed`` with a plain-dict payload.

    Payload is plain data (no domain objects) per the event-bus contract; all
    ids are stringified so a subscriber re-parses to UUID. Failures in any
    subscriber are swallowed by the bus, so the redemption itself never breaks.
    """
    event_bus.publish(
        COUPON_REDEEMED_EVENT,
        {
            "coupon_id": str(coupon.id),
            "coupon_code": coupon.code,
            "user_id": str(user_ref),
            "invoice_id": str(invoice_ref),
            "discount_amount": str(discount_amount),
            "sale_net_amount": str(sale_net_amount),
        },
    )


def checkout_price_adjustment(
    *,
    code: str,
    subtotal,
    user_id,
    scope: str,
    currency: str,
) -> PriceAdjustmentResult:
    """Validate ``code`` for ``scope`` and quote the money off ``subtotal``.

    Returns ``valid=False`` (+ error) for an unknown/expired/scope-mismatched
    code so the checkout rejects without mutating anything. On success the
    ``on_committed`` closure redeems the coupon + records the application after
    the invoice persists — exactly once.
    """
    session = db.session
    service = _build_service(session)
    discount_repo = DiscountRepository(session)
    subtotal = Decimal(str(subtotal))
    user_uuid = UUID(user_id) if user_id else None

    try:
        coupon = service.validate_coupon(code, user_uuid, subtotal)
    except CouponValidationError as exc:
        return PriceAdjustmentResult(valid=False, error=str(exc))

    discount = discount_repo.find_by_id(coupon.discount_id)
    if not discount:
        return PriceAdjustmentResult(valid=False, error="Discount is not available")

    # Scope correctness: GLOBAL applies to any checkout; otherwise the rule's
    # scope must match (e.g. an ECOMMERCE-only code on a SUBSCRIPTION checkout).
    if discount.scope != DiscountScope.GLOBAL and discount.scope.value != scope:
        return PriceAdjustmentResult(
            valid=False, error="This coupon is not valid for this checkout"
        )

    amount = service.compute_discount_amount(discount, subtotal)
    if amount <= 0:
        return PriceAdjustmentResult(valid=True, discount_amount=Decimal("0"))

    code_upper = coupon.code
    discount_id = discount.id
    original_subtotal = subtotal

    def on_committed(invoice_id: str, committed_user_id: str) -> None:
        commit_session = db.session
        commit_service = _build_service(commit_session)
        fresh_coupon = CouponRepository(commit_session).find_by_code(code_upper)
        if not fresh_coupon:
            return
        user_ref = UUID(committed_user_id)
        invoice_ref = UUID(invoice_id)
        commit_service.redeem_coupon(fresh_coupon, user_ref, invoice_ref, amount)
        commit_service.record_application(
            discount_id=discount_id,
            invoice_id=invoice_ref,
            user_id=user_ref,
            original_amount=original_subtotal,
            discount_amount=amount,
            coupon_id=fresh_coupon.id,
        )
        # Additive domain signal (S92 B2): announce the redemption so other
        # plugins (e.g. referral) can react — pay an issuer commission — without
        # the discount plugin knowing they exist. The event bus inverts the
        # dependency (Open/Closed); discount imports nothing referral-specific.
        _publish_coupon_redeemed(
            coupon=fresh_coupon,
            user_ref=user_ref,
            invoice_ref=invoice_ref,
            discount_amount=amount,
            sale_net_amount=original_subtotal,
        )

    return PriceAdjustmentResult(
        valid=True,
        discount_amount=amount,
        label=f"Coupon {coupon.code}",
        on_committed=on_committed,
    )
