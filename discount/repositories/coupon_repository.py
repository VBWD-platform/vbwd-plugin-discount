"""Coupon repository."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from plugins.discount.discount.models.coupon import Coupon


class CouponRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, coupon_id: UUID) -> Optional[Coupon]:
        return self._session.query(Coupon).filter_by(id=coupon_id).first()

    def find_by_code(self, code: str) -> Optional[Coupon]:
        return self._session.query(Coupon).filter_by(code=code.upper()).first()

    def find_by_discount(self, discount_id: UUID) -> list[Coupon]:
        return self._session.query(Coupon).filter_by(discount_id=discount_id).all()

    def find_all(self, limit: int = 50, offset: int = 0) -> list[Coupon]:
        return (
            self._session.query(Coupon)
            .order_by(Coupon.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def save(self, coupon: Coupon) -> Coupon:
        self._session.add(coupon)
        self._session.commit()
        return coupon

    def delete(self, coupon: Coupon) -> None:
        self._session.delete(coupon)
        self._session.commit()
