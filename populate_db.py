"""Discount plugin demo data — idempotent seeder."""
import logging
from decimal import Decimal
from uuid import uuid4

from vbwd.extensions import db

logger = logging.getLogger(__name__)


def populate(app=None):
    """Populate discount demo data (idempotent)."""
    from plugins.discount.discount.models.discount import (
        Discount,
        DiscountType,
        DiscountScope,
    )
    from plugins.discount.discount.models.coupon import Coupon

    created_count = 0

    # --- Discounts ---
    discounts_data = [
        {
            "name": "Summer Sale 20%",
            "slug": "summer-sale-20",
            "discount_type": DiscountType.PERCENTAGE,
            "value": Decimal("20.00"),
            "scope": DiscountScope.GLOBAL,
            "is_active": True,
            "stackable": False,
            "priority": 10,
        },
        {
            "name": "New Customer €5 Off",
            "slug": "new-customer-5-off",
            "discount_type": DiscountType.FIXED_AMOUNT,
            "value": Decimal("5.00"),
            "currency": "EUR",
            "scope": DiscountScope.ECOMMERCE,
            "min_order_amount": Decimal("25.00"),
            "max_uses_per_user": 1,
            "is_active": True,
            "stackable": False,
            "priority": 20,
        },
        {
            "name": "Free Shipping Over €50",
            "slug": "free-shipping-50",
            "discount_type": DiscountType.FREE_SHIPPING,
            "value": Decimal("0.00"),
            "scope": DiscountScope.ECOMMERCE,
            "min_order_amount": Decimal("50.00"),
            "is_active": True,
            "stackable": True,
            "priority": 50,
        },
        {
            "name": "Subscription 30% First 2 Months",
            "slug": "sub-30-first-2",
            "discount_type": DiscountType.PERCENTAGE,
            "value": Decimal("30.00"),
            "scope": DiscountScope.SUBSCRIPTION,
            "conditions": {"max_billing_cycles": 2},
            "is_active": True,
            "stackable": False,
            "priority": 10,
        },
        {
            "name": "Early Bird Booking 15%",
            "slug": "early-bird-booking-15",
            "discount_type": DiscountType.PERCENTAGE,
            "value": Decimal("15.00"),
            "scope": DiscountScope.BOOKING,
            "conditions": {"days_before_event": 14},
            "is_active": True,
            "stackable": False,
            "priority": 10,
        },
    ]

    discount_map = {}
    for discount_data in discounts_data:
        existing = (
            db.session.query(Discount).filter_by(slug=discount_data["slug"]).first()
        )
        if not existing:
            discount = Discount(id=uuid4(), **discount_data)
            db.session.add(discount)
            db.session.flush()
            discount_map[discount_data["slug"]] = discount
            created_count += 1
            logger.info("[discount] Created discount: %s", discount_data["name"])
        else:
            discount_map[discount_data["slug"]] = existing

    # --- Coupons ---
    coupons_data = [
        {
            "code": "SUMMER2026",
            "discount_slug": "summer-sale-20",
            "max_uses": 500,
            "max_uses_per_user": 1,
        },
        {
            "code": "WELCOME5",
            "discount_slug": "new-customer-5-off",
            "max_uses": 1000,
            "max_uses_per_user": 1,
        },
        {
            "code": "FREESHIP",
            "discount_slug": "free-shipping-50",
            "max_uses": None,
            "max_uses_per_user": None,
        },
        {
            "code": "SUB30",
            "discount_slug": "sub-30-first-2",
            "max_uses": 200,
            "max_uses_per_user": 1,
        },
        {
            "code": "EARLYBIRD",
            "discount_slug": "early-bird-booking-15",
            "max_uses": 100,
            "max_uses_per_user": 3,
        },
    ]

    for coupon_data in coupons_data:
        existing = db.session.query(Coupon).filter_by(code=coupon_data["code"]).first()
        if not existing:
            discount = discount_map.get(coupon_data["discount_slug"])
            if discount:
                coupon = Coupon(
                    id=uuid4(),
                    code=coupon_data["code"],
                    discount_id=discount.id,
                    max_uses=coupon_data["max_uses"],
                    max_uses_per_user=coupon_data["max_uses_per_user"],
                    is_active=True,
                )
                db.session.add(coupon)
                created_count += 1
                logger.info("[discount] Created coupon: %s", coupon_data["code"])

    if created_count:
        db.session.commit()
        logger.info("[discount] populate_db: created %d records", created_count)
    else:
        logger.info("[discount] populate_db: all data already exists")

    # Email templates
    _populate_email_templates()


def _populate_email_templates():
    """Import discount email templates."""
    import json
    import os

    templates_path = os.path.join(
        os.path.dirname(__file__),
        "docs",
        "imports",
        "email",
        "discount-email-templates.json",
    )
    if not os.path.exists(templates_path):
        return

    try:
        from plugins.email.src.models.email_template import EmailTemplate
    except ImportError:
        return

    with open(templates_path) as fh:
        templates = json.load(fh)

    for tpl in templates:
        existing = (
            db.session.query(EmailTemplate)
            .filter_by(event_type=tpl["event_type"])
            .first()
        )
        if not existing:
            db.session.add(
                EmailTemplate(
                    id=uuid4(),
                    event_type=tpl["event_type"],
                    subject=tpl["subject"],
                    html_body=tpl["html_body"],
                    text_body=tpl["text_body"],
                    is_active=tpl.get("is_active", True),
                )
            )
            logger.info("[discount] Created email template: %s", tpl["event_type"])

    db.session.commit()
