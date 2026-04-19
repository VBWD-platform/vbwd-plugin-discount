"""DiscountApplication model — audit log of applied discounts."""
from sqlalchemy.dialects.postgresql import UUID
from vbwd.extensions import db
from vbwd.models.base import BaseModel


class DiscountApplication(BaseModel):
    """Audit record: which discount was applied to which line item."""

    __tablename__ = "discount_application"

    discount_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("discount.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("vbwd_user_invoice.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_item_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("vbwd_invoice_line_item.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("vbwd_user.id", ondelete="CASCADE"),
        nullable=False,
    )
    original_amount = db.Column(db.Numeric(10, 2), nullable=False)
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False)
    final_amount = db.Column(db.Numeric(10, 2), nullable=False)
    coupon_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("coupon.id", ondelete="SET NULL"),
        nullable=True,
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "discount_id": str(self.discount_id),
            "invoice_id": str(self.invoice_id),
            "line_item_id": str(self.line_item_id) if self.line_item_id else None,
            "user_id": str(self.user_id),
            "original_amount": str(self.original_amount),
            "discount_amount": str(self.discount_amount),
            "final_amount": str(self.final_amount),
            "coupon_id": str(self.coupon_id) if self.coupon_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<DiscountApplication(discount={self.discount_id}, amount=-{self.discount_amount})>"
