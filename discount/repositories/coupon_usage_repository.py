"""CouponUsage repository."""
from uuid import UUID

from sqlalchemy.orm import Session

from plugins.discount.discount.models.coupon_usage import CouponUsage


class CouponUsageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_coupon(
        self, coupon_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[CouponUsage]:
        return (
            self._session.query(CouponUsage)
            .filter_by(coupon_id=coupon_id)
            .order_by(CouponUsage.used_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def count_by_coupon(self, coupon_id: UUID) -> int:
        return self._session.query(CouponUsage).filter_by(coupon_id=coupon_id).count()

    def count_by_coupon_and_user(self, coupon_id: UUID, user_id: UUID) -> int:
        return (
            self._session.query(CouponUsage)
            .filter_by(coupon_id=coupon_id, user_id=user_id)
            .count()
        )

    def save(self, usage: CouponUsage) -> CouponUsage:
        self._session.add(usage)
        self._session.commit()
        return usage
