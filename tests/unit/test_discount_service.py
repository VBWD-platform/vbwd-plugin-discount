"""Unit tests for DiscountService."""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from plugins.discount.discount.interfaces import DiscountContext
from plugins.discount.discount.registry import DiscountRuleRegistry
from plugins.discount.discount.services.discount_service import (
    DiscountService,
    CouponValidationError,
)

MOCK_NOW = datetime(2026, 3, 30, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def registry():
    return DiscountRuleRegistry()


@pytest.fixture
def discount_repo():
    return MagicMock()


@pytest.fixture
def coupon_repo():
    return MagicMock()


@pytest.fixture
def usage_repo():
    return MagicMock()


@pytest.fixture
def application_repo():
    return MagicMock()


@pytest.fixture(autouse=True)
def mock_utcnow():
    with patch(
        "plugins.discount.discount.services.discount_service.utcnow",
        return_value=MOCK_NOW,
    ):
        yield


@pytest.fixture
def service(registry, discount_repo, coupon_repo, usage_repo, application_repo):
    return DiscountService(
        registry=registry,
        discount_repo=discount_repo,
        coupon_repo=coupon_repo,
        usage_repo=usage_repo,
        application_repo=application_repo,
    )


def _make_discount(**kwargs):
    defaults = {
        "id": uuid4(),
        "name": "Test Discount",
        "slug": "test-discount",
        "discount_type": MagicMock(value="PERCENTAGE"),
        "value": Decimal("20.00"),
        "scope": MagicMock(value="GLOBAL"),
        "is_active": True,
        "min_order_amount": None,
        "max_discount_amount": None,
        "max_uses": None,
        "current_uses": 0,
        "starts_at": None,
        "expires_at": None,
    }
    defaults.update(kwargs)
    mock = MagicMock()
    for key, value in defaults.items():
        setattr(mock, key, value)
    return mock


def _make_coupon(**kwargs):
    defaults = {
        "id": uuid4(),
        "code": "TEST20",
        "discount_id": uuid4(),
        "is_active": True,
        "max_uses": None,
        "max_uses_per_user": None,
        "current_uses": 0,
        "starts_at": None,
        "expires_at": None,
    }
    defaults.update(kwargs)
    mock = MagicMock()
    for key, value in defaults.items():
        setattr(mock, key, value)
    return mock


class TestValidateCoupon:
    def test_valid_coupon(self, service, coupon_repo, discount_repo):
        coupon = _make_coupon()
        discount = _make_discount(id=coupon.discount_id)
        coupon_repo.find_by_code.return_value = coupon
        discount_repo.find_by_id.return_value = discount

        result = service.validate_coupon("TEST20", uuid4(), Decimal("100.00"))
        assert result is coupon

    def test_coupon_not_found(self, service, coupon_repo):
        coupon_repo.find_by_code.return_value = None
        with pytest.raises(CouponValidationError, match="not found"):
            service.validate_coupon("INVALID", uuid4(), Decimal("100.00"))

    def test_inactive_coupon(self, service, coupon_repo):
        coupon = _make_coupon(is_active=False)
        coupon_repo.find_by_code.return_value = coupon
        with pytest.raises(CouponValidationError, match="inactive"):
            service.validate_coupon("TEST20", uuid4(), Decimal("100.00"))

    def test_expired_coupon(self, service, coupon_repo):
        coupon = _make_coupon(expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc))
        coupon_repo.find_by_code.return_value = coupon
        with pytest.raises(CouponValidationError, match="expired"):
            service.validate_coupon("TEST20", uuid4(), Decimal("100.00"))

    def test_max_uses_reached(self, service, coupon_repo):
        coupon = _make_coupon(max_uses=10, current_uses=10)
        coupon_repo.find_by_code.return_value = coupon
        with pytest.raises(CouponValidationError, match="limit reached"):
            service.validate_coupon("TEST20", uuid4(), Decimal("100.00"))

    def test_per_user_limit_reached(
        self, service, coupon_repo, usage_repo, discount_repo
    ):
        user_id = uuid4()
        coupon = _make_coupon(max_uses_per_user=1)
        discount = _make_discount(id=coupon.discount_id)
        coupon_repo.find_by_code.return_value = coupon
        discount_repo.find_by_id.return_value = discount
        usage_repo.count_by_coupon_and_user.return_value = 1

        with pytest.raises(CouponValidationError, match="already used"):
            service.validate_coupon("TEST20", user_id, Decimal("100.00"))

    def test_min_order_not_met(self, service, coupon_repo, discount_repo):
        coupon = _make_coupon()
        discount = _make_discount(
            id=coupon.discount_id, min_order_amount=Decimal("50.00")
        )
        coupon_repo.find_by_code.return_value = coupon
        discount_repo.find_by_id.return_value = discount

        with pytest.raises(CouponValidationError, match="Minimum order"):
            service.validate_coupon("TEST20", uuid4(), Decimal("25.00"))


class TestRedeemCoupon:
    def test_redeem_increments_counters(
        self, service, coupon_repo, usage_repo, discount_repo
    ):
        coupon = _make_coupon(current_uses=5)
        discount = _make_discount(id=coupon.discount_id, current_uses=10)
        discount_repo.find_by_id.return_value = discount

        service.redeem_coupon(coupon, uuid4(), uuid4(), Decimal("15.00"))

        assert coupon.current_uses == 6
        assert discount.current_uses == 11
        usage_repo.save.assert_called_once()
        coupon_repo.save.assert_called_once()


class TestCalculateDiscount:
    def test_percentage_discount(self, service, registry):
        discount = _make_discount(
            discount_type=MagicMock(value="PERCENTAGE"),
            value=Decimal("20.00"),
            scope=MagicMock(value="GLOBAL"),
            max_discount_amount=None,
        )

        amount = service.calculate_discount(
            discount=discount,
            line_item_type="CUSTOM",
            line_item_extra_data={},
            unit_price=Decimal("50.00"),
            quantity=2,
            context=DiscountContext(
                user_id=None,
                invoice_id=None,
                coupon_code=None,
                cart_total=Decimal("100"),
                line_item_count=1,
            ),
        )
        assert amount == Decimal("20.00")

    def test_max_discount_cap(self, service, registry):
        discount = _make_discount(
            discount_type=MagicMock(value="PERCENTAGE"),
            value=Decimal("50.00"),
            scope=MagicMock(value="GLOBAL"),
            max_discount_amount=Decimal("10.00"),
        )

        amount = service.calculate_discount(
            discount=discount,
            line_item_type="CUSTOM",
            line_item_extra_data={},
            unit_price=Decimal("100.00"),
            quantity=1,
            context=DiscountContext(
                user_id=None,
                invoice_id=None,
                coupon_code=None,
                cart_total=Decimal("100"),
                line_item_count=1,
            ),
        )
        assert amount == Decimal("10.00")
