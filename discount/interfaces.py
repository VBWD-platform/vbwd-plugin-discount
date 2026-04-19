"""Discount plugin interfaces — IDiscountRule + data classes."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID


class DiscountScope(str, Enum):
    """Which line item types a discount can apply to."""

    GLOBAL = "GLOBAL"
    ECOMMERCE = "ECOMMERCE"
    SUBSCRIPTION = "SUBSCRIPTION"
    BOOKING = "BOOKING"


@dataclass
class DiscountContext:
    """Context passed to discount rule evaluation."""

    user_id: Optional[UUID]
    invoice_id: Optional[UUID]
    coupon_code: Optional[str]
    cart_total: Decimal
    line_item_count: int
    metadata: dict = field(default_factory=dict)


@dataclass
class DiscountResult:
    """Result of a single discount rule evaluation."""

    discount_id: UUID
    line_item_id: Optional[UUID]
    original_amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    reason: str
    coupon_id: Optional[UUID] = None


class IDiscountRule(ABC):
    """Interface for plugin-specific discount rules.

    Each billing plugin (subscription, ecommerce, booking) registers
    its own implementation. The discount plugin orchestrates evaluation.
    """

    @abstractmethod
    def can_apply(
        self,
        line_item_type: str,
        line_item_extra_data: dict,
        discount_scope: DiscountScope,
    ) -> bool:
        """Check if this rule can evaluate the given line item + discount scope."""

    @abstractmethod
    def evaluate(
        self,
        line_item_type: str,
        line_item_extra_data: dict,
        unit_price: Decimal,
        quantity: int,
        discount_type: str,
        discount_value: Decimal,
        context: DiscountContext,
    ) -> Decimal:
        """Calculate discount amount. Returns 0 if not applicable."""

    @abstractmethod
    def get_supported_scopes(self) -> list[DiscountScope]:
        """Which discount scopes this rule handles."""
