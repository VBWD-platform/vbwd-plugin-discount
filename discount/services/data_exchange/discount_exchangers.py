"""Discount entity exchangers for the S46 data-exchange seam (S46.6).

Exposes the discount rules + coupons through the core ``EntityExchanger``
contract so they appear on the generic Settings → Import/Export page and the
per-list controls.

Entities:

* ``discount_rules`` (``DiscountRule``, natural key ``slug``) — import+export.
* ``discount_coupons`` (``Coupon``, natural key ``code``) — import+export. The
  coupon's NOT NULL FK ``discount_id`` points at a ``discount_rule`` row; on a
  same-instance round-trip the FK value is preserved (the rule is not wiped).

Design notes:

* **Reused perms** — the plugin already ships ``discount.discounts.*`` /
  ``discount.coupons.*``; each exchanger maps ``export_permission`` /
  ``import_permission`` onto those (single source of truth).
* **DRY** — both reuse :class:`BaseModelExchanger`; only the narrow
  ``_SessionModelRepository`` adapter is added (mirrors core / CMS).
* **No core change** — registration happens in ``DiscountPlugin.on_enable``
  through the shared ``db.session``; core imports no ``plugins.*`` module.

Engineering requirements (binding, restated): TDD-first; DevOps-first; SOLID
(one exchanger per entity, narrow ports); DI (session injected); DRY; Liskov;
clean code; no overengineering. Quality guard: ``bin/pre-commit-check.sh
--plugin discount --full``.
"""
from typing import Any, List, Optional

from vbwd.services.data_exchange.base_model_exchanger import BaseModelExchanger
from vbwd.services.data_exchange.port import CLUSTER_SALES, EntityExchanger
from vbwd.services.data_exchange.registry import data_exchange_registry

# Existing discount permissions (single source — DiscountPlugin.admin_permissions).
PERM_DISCOUNTS_VIEW = "discount.discounts.view"
PERM_DISCOUNTS_MANAGE = "discount.discounts.manage"
PERM_COUPONS_VIEW = "discount.coupons.view"
PERM_COUPONS_MANAGE = "discount.coupons.manage"


class _SessionModelRepository:
    """Narrow model repo satisfying the ``BaseModelExchanger`` contract (ISP).

    Mirrors core's / CMS's adapter: the discount repositories expose domain
    finders rather than the four flat methods the base exchanger needs.
    """

    def __init__(self, session: Any, model_class: type, natural_key: str) -> None:
        self._session = session
        self._model_class = model_class
        self._natural_key = natural_key

    def find_all(self) -> List[Any]:
        return self._session.query(self._model_class).all()

    def find_by_natural_key(self, value: Any) -> Optional[Any]:
        column = getattr(self._model_class, self._natural_key)
        return self._session.query(self._model_class).filter(column == value).first()

    def add(self, instance: Any) -> None:
        self._session.add(instance)

    def delete_all(self) -> None:
        self._session.query(self._model_class).delete()


class _PermissionMappedModelExchanger(BaseModelExchanger):
    """A ``BaseModelExchanger`` whose perms map onto existing discount perms."""

    def __init__(
        self,
        *,
        view_permission: str,
        manage_permission: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._view_permission = view_permission
        self._manage_permission = manage_permission

    @property
    def export_permission(self) -> str:
        return self._view_permission

    @property
    def import_permission(self) -> str:
        return self._manage_permission


def build_discount_exchangers(session: Any) -> List[EntityExchanger]:
    """Construct the discount exchangers bound to ``session``."""
    from plugins.discount.discount.models.coupon import Coupon
    from plugins.discount.discount.models.discount import DiscountRule

    return [
        _PermissionMappedModelExchanger(
            entity_key="discount_rules",
            label="Discount Rules",
            cluster=CLUSTER_SALES,
            natural_key="slug",
            model_class=DiscountRule,
            repository=_SessionModelRepository(session, DiscountRule, "slug"),
            session=session,
            public_fields=[
                "slug",
                "name",
                "discount_type",
                "value",
                "currency",
                "scope",
                "conditions",
                "min_order_amount",
                "max_discount_amount",
                "max_uses",
                "max_uses_per_user",
                "starts_at",
                "expires_at",
                "is_active",
                "stackable",
                "priority",
            ],
            supported_formats=frozenset({"json", "csv"}),
            view_permission=PERM_DISCOUNTS_VIEW,
            manage_permission=PERM_DISCOUNTS_MANAGE,
        ),
        _PermissionMappedModelExchanger(
            entity_key="discount_coupons",
            label="Discount Coupons",
            cluster=CLUSTER_SALES,
            natural_key="code",
            model_class=Coupon,
            repository=_SessionModelRepository(session, Coupon, "code"),
            session=session,
            public_fields=[
                "code",
                "discount_id",
                "max_uses",
                "max_uses_per_user",
                "is_active",
                "starts_at",
                "expires_at",
            ],
            supported_formats=frozenset({"json", "csv"}),
            view_permission=PERM_COUPONS_VIEW,
            manage_permission=PERM_COUPONS_MANAGE,
        ),
    ]


def register_discount_exchangers(session: Any) -> None:
    """Register the discount exchangers into the registry (idempotent).

    Called from ``DiscountPlugin.on_enable``. Re-registering replaces by key, so
    a repeat enable (per-test app) is clear-safe.
    """
    for exchanger in build_discount_exchangers(session):
        data_exchange_registry.register(exchanger)
