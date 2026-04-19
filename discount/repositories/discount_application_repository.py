"""DiscountApplication repository."""
from uuid import UUID

from sqlalchemy.orm import Session

from plugins.discount.discount.models.discount_application import DiscountApplication


class DiscountApplicationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_invoice(self, invoice_id: UUID) -> list[DiscountApplication]:
        return (
            self._session.query(DiscountApplication)
            .filter_by(invoice_id=invoice_id)
            .all()
        )

    def find_by_discount(self, discount_id: UUID, limit: int = 50, offset: int = 0) -> list[DiscountApplication]:
        return (
            self._session.query(DiscountApplication)
            .filter_by(discount_id=discount_id)
            .order_by(DiscountApplication.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def save(self, application: DiscountApplication) -> DiscountApplication:
        self._session.add(application)
        self._session.commit()
        return application
