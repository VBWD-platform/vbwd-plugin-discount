"""Integration: the discount plugin's checkout price adjustment end-to-end.

Seeds a DiscountRule + Coupon through the repos (no raw SQL) and drives the
``checkout_price_adjustment`` port the way the checkouts will:
  - a valid SUBSCRIPTION code quotes the right money off + a callable commit hook
  - a scope-mismatched code is rejected (valid=False)
  - an unknown code is rejected
  - on_committed redeems the coupon + records the application exactly once
"""
from decimal import Decimal
from uuid import uuid4

from vbwd.models.enums import UserRole, UserStatus
from vbwd.models.user import User
from vbwd.models.invoice import UserInvoice

from plugins.discount.discount.checkout_adjustment import checkout_price_adjustment
from plugins.discount.discount.models.coupon import Coupon
from plugins.discount.discount.models.discount import (
    DiscountRule,
    DiscountScope,
    DiscountType,
)
from plugins.discount.discount.repositories.coupon_repository import CouponRepository
from plugins.discount.discount.repositories.discount_application_repository import (
    DiscountApplicationRepository,
)
from plugins.discount.discount.repositories.discount_repository import (
    DiscountRepository,
)


def _seed_discount_and_coupon(session, *, code, scope, dtype, value, min_order=None):
    discount = DiscountRepository(session).save(
        DiscountRule(
            id=uuid4(),
            name=f"D {code}",
            slug=f"d-{code.lower()}",
            discount_type=dtype,
            value=Decimal(value),
            scope=scope,
            min_order_amount=Decimal(min_order) if min_order else None,
            is_active=True,
            priority=10,
        )
    )
    coupon = CouponRepository(session).save(
        Coupon(id=uuid4(), code=code, discount_id=discount.id, is_active=True)
    )
    return discount, coupon


def _seed_user(session) -> User:
    user = User(
        id=uuid4(),
        email=f"coupon-{uuid4().hex[:8]}@example.com",
        password_hash="x",
        status=UserStatus.ACTIVE,
        role=UserRole.USER,
    )
    session.add(user)
    session.commit()
    return user


def test_valid_subscription_coupon_quotes_discount(db):
    user = _seed_user(db.session)
    _seed_discount_and_coupon(
        db.session,
        code="SUB30",
        scope=DiscountScope.SUBSCRIPTION,
        dtype=DiscountType.PERCENTAGE,
        value="30.00",
    )

    result = checkout_price_adjustment(
        code="SUB30",
        subtotal=Decimal("100.00"),
        user_id=str(user.id),
        scope="SUBSCRIPTION",
        currency="EUR",
    )

    assert result.valid is True
    assert result.discount_amount == Decimal("30.00")
    assert result.label == "Coupon SUB30"
    assert callable(result.on_committed)


def test_global_coupon_applies_to_subscription(db):
    user = _seed_user(db.session)
    _seed_discount_and_coupon(
        db.session,
        code="SUMMER2026",
        scope=DiscountScope.GLOBAL,
        dtype=DiscountType.PERCENTAGE,
        value="20.00",
    )

    result = checkout_price_adjustment(
        code="SUMMER2026",
        subtotal=Decimal("100.00"),
        user_id=str(user.id),
        scope="SUBSCRIPTION",
        currency="EUR",
    )
    assert result.valid is True
    assert result.discount_amount == Decimal("20.00")


def test_scope_mismatched_coupon_is_rejected(db):
    user = _seed_user(db.session)
    _seed_discount_and_coupon(
        db.session,
        code="SHOPONLY",
        scope=DiscountScope.ECOMMERCE,
        dtype=DiscountType.FIXED_AMOUNT,
        value="5.00",
    )

    result = checkout_price_adjustment(
        code="SHOPONLY",
        subtotal=Decimal("100.00"),
        user_id=str(user.id),
        scope="SUBSCRIPTION",
        currency="EUR",
    )
    assert result.valid is False
    assert result.discount_amount == Decimal("0")
    assert "not valid" in (result.error or "").lower()


def test_unknown_coupon_is_rejected(db):
    user = _seed_user(db.session)
    result = checkout_price_adjustment(
        code="DOESNOTEXIST",
        subtotal=Decimal("100.00"),
        user_id=str(user.id),
        scope="SUBSCRIPTION",
        currency="EUR",
    )
    assert result.valid is False
    assert result.error


def test_on_committed_redeems_and_records_once(db):
    user = _seed_user(db.session)
    _discount, coupon = _seed_discount_and_coupon(
        db.session,
        code="REDEEM30",
        scope=DiscountScope.SUBSCRIPTION,
        dtype=DiscountType.PERCENTAGE,
        value="30.00",
    )
    invoice = UserInvoice(
        id=uuid4(),
        user_id=user.id,
        invoice_number=f"INV-{uuid4().hex[:8]}",
        amount=Decimal("70.00"),
    )
    db.session.add(invoice)
    db.session.commit()

    result = checkout_price_adjustment(
        code="REDEEM30",
        subtotal=Decimal("100.00"),
        user_id=str(user.id),
        scope="SUBSCRIPTION",
        currency="EUR",
    )
    assert result.valid is True

    result.on_committed(str(invoice.id), str(user.id))

    redeemed = CouponRepository(db.session).find_by_code("REDEEM30")
    assert redeemed.current_uses == 1
    applications = DiscountApplicationRepository(db.session).find_by_invoice(invoice.id)
    assert len(applications) == 1
    assert applications[0].discount_amount == Decimal("30.00")
