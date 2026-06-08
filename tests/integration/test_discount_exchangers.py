"""Integration: discount entity exchangers (real PG) — S46.6.

* ``discount_rules`` round-trips by ``slug`` (export → wipe → import → equal).
* ``discount_coupons`` round-trips by ``code`` (the coupon's ``discount_id`` FK
  is preserved on a same-instance round-trip — the rule is not wiped).
* registration: after ``DiscountPlugin._register_data_exchangers`` the
  exchangers appear in ``data_exchange_registry`` with cluster ``sales``.

Data is seeded through the ORM session (no raw SQL); the shared ``db`` fixture
creates + drops the test DB.

Engineering requirements (binding, restated): TDD-first; DevOps-first; SOLID/DI/
DRY; Liskov; no overengineering. Quality guard: ``bin/pre-commit-check.sh
--plugin discount --full``.
"""
import uuid

from vbwd.services.data_exchange.envelope import build_envelope, rows_to_csv
from vbwd.services.data_exchange.port import CLUSTER_SALES, ExportSelector
from plugins.discount.discount.models.coupon import Coupon
from plugins.discount.discount.models.discount import (
    DiscountRule,
    DiscountScope,
    DiscountType,
)
from plugins.discount.discount.services.data_exchange.discount_exchangers import (
    build_discount_exchangers,
)


def _exchangers(session):
    return {
        exchanger.entity_key: exchanger
        for exchanger in build_discount_exchangers(session)
    }


def _seed_rule(db):
    rule = DiscountRule(
        slug=f"rule-{uuid.uuid4().hex[:8]}",
        name="Spring Sale",
        discount_type=DiscountType.PERCENTAGE,
        value=10,
        scope=DiscountScope.GLOBAL,
    )
    db.session.add(rule)
    db.session.commit()
    return rule


class TestRulesRoundTrip:
    def test_round_trip_by_slug(self, db):
        rule = _seed_rule(db)
        slug = rule.slug
        exchanger = _exchangers(db.session)["discount_rules"]

        before = exchanger.export(ExportSelector(ids=[slug]), include_pii=False).rows
        assert before and before[0]["slug"] == slug

        db.session.query(DiscountRule).filter(DiscountRule.slug == slug).delete()
        db.session.commit()

        payload = build_envelope("discount_rules", before, instance="test")
        result = exchanger.import_(payload, mode="upsert", dry_run=False)
        assert result.created == 1

        rebuilt = (
            db.session.query(DiscountRule).filter(DiscountRule.slug == slug).first()
        )
        assert rebuilt is not None
        assert rebuilt.name == "Spring Sale"
        assert rebuilt.discount_type == DiscountType.PERCENTAGE


class TestCouponsRoundTrip:
    def test_round_trip_by_code(self, db):
        rule = _seed_rule(db)
        code = f"SAVE-{uuid.uuid4().hex[:6]}"
        db.session.add(Coupon(code=code, discount_id=rule.id, max_uses=100))
        db.session.commit()

        exchanger = _exchangers(db.session)["discount_coupons"]
        before = exchanger.export(ExportSelector(ids=[code]), include_pii=False).rows
        assert before and before[0]["code"] == code

        db.session.query(Coupon).filter(Coupon.code == code).delete()
        db.session.commit()

        payload = build_envelope("discount_coupons", before, instance="test")
        exchanger.import_(payload, mode="upsert", dry_run=False)
        rebuilt = db.session.query(Coupon).filter(Coupon.code == code).first()
        assert rebuilt is not None
        assert rebuilt.max_uses == 100
        assert str(rebuilt.discount_id) == str(rule.id)


class TestCsvExport:
    def test_discount_rules_csv_export(self, db):
        rule = _seed_rule(db)
        exchanger = _exchangers(db.session)["discount_rules"]
        assert "csv" in exchanger.supported_formats
        rows = exchanger.export(ExportSelector(ids=[rule.slug]), include_pii=False).rows
        csv_text = rows_to_csv(rows)
        assert "slug" in csv_text.splitlines()[0]
        assert rule.slug in csv_text


class TestRegistration:
    def test_on_enable_registers_discount_exchangers(self, db):
        from vbwd.services.data_exchange.registry import data_exchange_registry
        from plugins.discount import DiscountPlugin

        plugin = DiscountPlugin()
        plugin.initialize({})
        plugin._register_data_exchangers()

        by_key = {
            exchanger.entity_key: exchanger
            for exchanger in data_exchange_registry.all()
        }
        for key in ("discount_rules", "discount_coupons"):
            assert key in by_key
            assert by_key[key].cluster == CLUSTER_SALES
