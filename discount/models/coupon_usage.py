"""CouponUsage model — tracks coupon redemptions."""
from sqlalchemy.dialects.postgresql import UUID
from vbwd.extensions import db
from vbwd.models.base import BaseModel
from vbwd.utils.datetime_utils import utcnow


class CouponUsage(BaseModel):
    """Record of a coupon being redeemed by a user on an invoice."""

    __tablename__ = "discount_coupon_usage"

    coupon_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("discount_coupon.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("vbwd_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("vbwd_user_invoice.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False)
    used_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "coupon_id": str(self.coupon_id),
            "user_id": str(self.user_id),
            "invoice_id": str(self.invoice_id) if self.invoice_id else None,
            "discount_amount": str(self.discount_amount),
            "used_at": self.used_at.isoformat() if self.used_at else None,
        }

    def __repr__(self) -> str:
        return f"<CouponUsage(coupon={self.coupon_id}, user={self.user_id})>"
