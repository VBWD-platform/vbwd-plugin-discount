"""Discount model — the rule definition."""
import enum

from sqlalchemy.dialects.postgresql import JSONB
from vbwd.extensions import db
from vbwd.models.base import BaseModel


class DiscountType(str, enum.Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED_AMOUNT = "FIXED_AMOUNT"
    FREE_SHIPPING = "FREE_SHIPPING"
    BUY_X_GET_Y = "BUY_X_GET_Y"


class DiscountScope(str, enum.Enum):
    GLOBAL = "GLOBAL"
    ECOMMERCE = "ECOMMERCE"
    SUBSCRIPTION = "SUBSCRIPTION"
    BOOKING = "BOOKING"


class Discount(BaseModel):
    """Discount rule — percentage, fixed amount, free shipping, or buy-X-get-Y."""

    __tablename__ = "discount"

    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), nullable=False, unique=True, index=True)
    discount_type = db.Column(
        db.Enum(DiscountType, name="discount_type_enum", native_enum=True, create_constraint=False),
        nullable=False,
    )
    value = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=True)

    scope = db.Column(
        db.Enum(DiscountScope, name="discount_scope_enum", native_enum=True, create_constraint=False),
        nullable=False,
        default=DiscountScope.GLOBAL,
    )
    conditions = db.Column(JSONB, nullable=True, default=dict)

    min_order_amount = db.Column(db.Numeric(10, 2), nullable=True)
    max_discount_amount = db.Column(db.Numeric(10, 2), nullable=True)
    max_uses = db.Column(db.Integer, nullable=True)
    max_uses_per_user = db.Column(db.Integer, nullable=True)
    current_uses = db.Column(db.Integer, nullable=False, default=0)

    starts_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    stackable = db.Column(db.Boolean, nullable=False, default=False)
    priority = db.Column(db.Integer, nullable=False, default=100)

    coupons = db.relationship("Coupon", backref="discount", lazy="selectin", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "discount_type": self.discount_type.value,
            "value": str(self.value),
            "currency": self.currency,
            "scope": self.scope.value,
            "conditions": self.conditions,
            "min_order_amount": str(self.min_order_amount) if self.min_order_amount else None,
            "max_discount_amount": str(self.max_discount_amount) if self.max_discount_amount else None,
            "max_uses": self.max_uses,
            "max_uses_per_user": self.max_uses_per_user,
            "current_uses": self.current_uses,
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "stackable": self.stackable,
            "priority": self.priority,
            "coupons": [c.to_dict() for c in self.coupons] if self.coupons else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Discount(name='{self.name}', type={self.discount_type.value}, scope={self.scope.value})>"
