"""Discount repository."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from plugins.discount.discount.models.discount import Discount, DiscountScope


class DiscountRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, discount_id: UUID) -> Optional[Discount]:
        return self._session.query(Discount).filter_by(id=discount_id).first()

    def find_by_slug(self, slug: str) -> Optional[Discount]:
        return self._session.query(Discount).filter_by(slug=slug).first()

    def find_active(self, scope: Optional[DiscountScope] = None) -> list[Discount]:
        query = self._session.query(Discount).filter_by(is_active=True)
        if scope:
            query = query.filter(
                (Discount.scope == scope) | (Discount.scope == DiscountScope.GLOBAL)
            )
        return query.order_by(Discount.priority).all()

    def find_all(self, limit: int = 50, offset: int = 0) -> list[Discount]:
        return (
            self._session.query(Discount)
            .order_by(Discount.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def save(self, discount: Discount) -> Discount:
        self._session.add(discount)
        self._session.commit()
        return discount

    def delete(self, discount: Discount) -> None:
        self._session.delete(discount)
        self._session.commit()
