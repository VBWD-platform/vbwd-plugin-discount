"""DiscountRule repository."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from plugins.discount.discount.models.discount import DiscountRule, DiscountScope


class DiscountRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, discount_id: UUID) -> Optional[DiscountRule]:
        return self._session.query(DiscountRule).filter_by(id=discount_id).first()

    def find_by_slug(self, slug: str) -> Optional[DiscountRule]:
        return self._session.query(DiscountRule).filter_by(slug=slug).first()

    def find_active(self, scope: Optional[DiscountScope] = None) -> list[DiscountRule]:
        query = self._session.query(DiscountRule).filter_by(is_active=True)
        if scope:
            query = query.filter(
                (DiscountRule.scope == scope)
                | (DiscountRule.scope == DiscountScope.GLOBAL)
            )
        return query.order_by(DiscountRule.priority).all()

    def find_all(self, limit: int = 50, offset: int = 0) -> list[DiscountRule]:
        return (
            self._session.query(DiscountRule)
            .order_by(DiscountRule.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def save(self, discount: DiscountRule) -> DiscountRule:
        self._session.add(discount)
        self._session.commit()
        return discount

    def delete(self, discount: DiscountRule) -> None:
        self._session.delete(discount)
        self._session.commit()
