"""Coupon model — user-facing code linked to a Discount."""
from sqlalchemy.dialects.postgresql import UUID
from vbwd.extensions import db
from vbwd.models.base import BaseModel


class Coupon(BaseModel):
    """Coupon code linked to a discount rule."""

    __tablename__ = "discount_coupon"

    code = db.Column(db.String(50), nullable=False, unique=True, index=True)
    discount_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("discount_rule.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    max_uses = db.Column(db.Integer, nullable=True)
    max_uses_per_user = db.Column(db.Integer, nullable=True)
    current_uses = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    starts_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)

    usages = db.relationship(
        "CouponUsage", backref="coupon", lazy="selectin", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "code": self.code,
            "discount_id": str(self.discount_id),
            "max_uses": self.max_uses,
            "max_uses_per_user": self.max_uses_per_user,
            "current_uses": self.current_uses,
            "is_active": self.is_active,
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Coupon(code='{self.code}')>"
