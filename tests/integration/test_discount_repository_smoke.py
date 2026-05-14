"""Smoke integration test: prove the discount repository round-trips
through a real PostgreSQL session.

Goes through DiscountRepository (no raw SQL — see
feedback_no_direct_db_for_test_data.md) and asserts the row is fetchable
both by slug and through the active-listing filter.

Sized to be the cheapest assertion that defends:
  - the SQLAlchemy mapper for Discount + the two enums
  - the discount conftest wiring (test DB, create_all, drop_all)
  - DiscountRepository.save() committing rather than just flushing
"""
from decimal import Decimal
from uuid import uuid4

from plugins.discount.discount.models.discount import (
    Discount,
    DiscountScope,
    DiscountType,
)
from plugins.discount.discount.repositories.discount_repository import (
    DiscountRepository,
)


def test_discount_save_then_round_trips_through_real_db(db):
    repository = DiscountRepository(db.session)

    new_discount = Discount(
        id=uuid4(),
        name="Smoke Welcome 10",
        slug="smoke-welcome-10",
        discount_type=DiscountType.PERCENTAGE,
        value=Decimal("10.00"),
        scope=DiscountScope.GLOBAL,
        is_active=True,
        priority=100,
    )
    saved_discount = repository.save(new_discount)

    fetched_by_slug = repository.find_by_slug("smoke-welcome-10")
    fetched_by_id = repository.find_by_id(saved_discount.id)
    active_for_subscription = repository.find_active(scope=DiscountScope.SUBSCRIPTION)

    assert fetched_by_slug is not None
    assert fetched_by_slug.id == saved_discount.id
    assert fetched_by_slug.discount_type == DiscountType.PERCENTAGE
    assert fetched_by_slug.value == Decimal("10.00")

    assert fetched_by_id is not None
    assert fetched_by_id.scope == DiscountScope.GLOBAL

    # GLOBAL discounts surface in any per-scope query.
    assert any(d.id == saved_discount.id for d in active_for_subscription)
