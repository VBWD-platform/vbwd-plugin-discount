"""Discount plugin routes — public coupon validation + admin CRUD."""
from decimal import Decimal
from uuid import uuid4

from flask import Blueprint, jsonify, request, g
from vbwd.extensions import db
from vbwd.middleware.auth import require_auth, require_admin, require_permission

from plugins.discount.discount.models.discount import Discount, DiscountType, DiscountScope
from plugins.discount.discount.models.coupon import Coupon
from plugins.discount.discount.repositories.discount_repository import DiscountRepository
from plugins.discount.discount.repositories.coupon_repository import CouponRepository
from plugins.discount.discount.repositories.coupon_usage_repository import CouponUsageRepository
from plugins.discount.discount.repositories.discount_application_repository import DiscountApplicationRepository
from plugins.discount.discount.services.discount_service import DiscountService, CouponValidationError

discount_bp = Blueprint("discount", __name__)


def _service() -> DiscountService:
    from plugins.discount import _discount_registry

    return DiscountService(
        registry=_discount_registry,
        discount_repo=DiscountRepository(db.session),
        coupon_repo=CouponRepository(db.session),
        usage_repo=CouponUsageRepository(db.session),
        application_repo=DiscountApplicationRepository(db.session),
    )


# ── Public: Coupon Validation ───────────────────────────────────────────


@discount_bp.route("/api/v1/coupons/validate", methods=["POST"])
def validate_coupon():
    """Validate a coupon code against a cart total."""
    data = request.get_json() or {}
    code = data.get("code", "").strip()
    cart_total = Decimal(str(data.get("cart_total", "0")))

    if not code:
        return jsonify({"error": "Coupon code is required"}), 400

    user_id = getattr(g, "user_id", None)

    try:
        coupon = _service().validate_coupon(code, user_id, cart_total)
        discount = DiscountRepository(db.session).find_by_id(coupon.discount_id)
        return (
            jsonify(
                {
                    "valid": True,
                    "coupon": coupon.to_dict(),
                    "discount": discount.to_dict() if discount else None,
                }
            ),
            200,
        )
    except CouponValidationError as validation_error:
        return jsonify({"valid": False, "error": str(validation_error)}), 200


# ── Admin: Discounts ────────────────────────────────────────────────────


@discount_bp.route("/api/v1/admin/discounts", methods=["GET"])
@require_auth
@require_admin
@require_permission("discount.discounts.view")
def admin_list_discounts():
    """List all discounts."""
    repo = DiscountRepository(db.session)
    discounts = repo.find_all()
    return jsonify({"discounts": [d.to_dict() for d in discounts]}), 200


@discount_bp.route("/api/v1/admin/discounts", methods=["POST"])
@require_auth
@require_admin
@require_permission("discount.discounts.manage")
def admin_create_discount():
    """Create a discount."""
    data = request.get_json() or {}
    if not data.get("name"):
        return jsonify({"error": "Name is required"}), 400

    slug = data.get("slug") or data["name"].lower().replace(" ", "-")
    repo = DiscountRepository(db.session)

    if repo.find_by_slug(slug):
        return jsonify({"error": f"Discount with slug '{slug}' already exists"}), 400

    discount = Discount(
        id=uuid4(),
        name=data["name"],
        slug=slug,
        discount_type=DiscountType(data.get("discount_type", "PERCENTAGE")),
        value=Decimal(str(data.get("value", "0"))),
        currency=data.get("currency"),
        scope=DiscountScope(data.get("scope", "GLOBAL")),
        conditions=data.get("conditions", {}),
        min_order_amount=Decimal(str(data["min_order_amount"])) if data.get("min_order_amount") else None,
        max_discount_amount=Decimal(str(data["max_discount_amount"])) if data.get("max_discount_amount") else None,
        max_uses=data.get("max_uses"),
        max_uses_per_user=data.get("max_uses_per_user"),
        starts_at=data.get("starts_at"),
        expires_at=data.get("expires_at"),
        is_active=data.get("is_active", True),
        stackable=data.get("stackable", False),
        priority=data.get("priority", 100),
    )
    repo.save(discount)
    return jsonify({"discount": discount.to_dict()}), 201


@discount_bp.route("/api/v1/admin/discounts/<discount_id>", methods=["GET"])
@require_auth
@require_admin
@require_permission("discount.discounts.view")
def admin_get_discount(discount_id):
    """Get discount detail."""
    repo = DiscountRepository(db.session)
    discount = repo.find_by_id(discount_id)
    if not discount:
        return jsonify({"error": "Discount not found"}), 404
    return jsonify({"discount": discount.to_dict()}), 200


@discount_bp.route("/api/v1/admin/discounts/<discount_id>", methods=["PUT"])
@require_auth
@require_admin
@require_permission("discount.discounts.manage")
def admin_update_discount(discount_id):
    """Update a discount."""
    repo = DiscountRepository(db.session)
    discount = repo.find_by_id(discount_id)
    if not discount:
        return jsonify({"error": "Discount not found"}), 404

    data = request.get_json() or {}
    for field_name in [
        "name",
        "slug",
        "currency",
        "conditions",
        "max_uses",
        "max_uses_per_user",
        "is_active",
        "stackable",
        "priority",
        "starts_at",
        "expires_at",
    ]:
        if field_name in data:
            setattr(discount, field_name, data[field_name])

    if "discount_type" in data:
        discount.discount_type = DiscountType(data["discount_type"])
    if "scope" in data:
        discount.scope = DiscountScope(data["scope"])
    if "value" in data:
        discount.value = Decimal(str(data["value"]))
    if "min_order_amount" in data:
        discount.min_order_amount = Decimal(str(data["min_order_amount"])) if data["min_order_amount"] else None
    if "max_discount_amount" in data:
        discount.max_discount_amount = (
            Decimal(str(data["max_discount_amount"])) if data["max_discount_amount"] else None
        )

    repo.save(discount)
    return jsonify({"discount": discount.to_dict()}), 200


@discount_bp.route("/api/v1/admin/discounts/<discount_id>", methods=["DELETE"])
@require_auth
@require_admin
@require_permission("discount.discounts.manage")
def admin_delete_discount(discount_id):
    """Delete a discount."""
    repo = DiscountRepository(db.session)
    discount = repo.find_by_id(discount_id)
    if not discount:
        return jsonify({"error": "Discount not found"}), 404
    repo.delete(discount)
    return jsonify({"message": "Discount deleted"}), 200


# ── Admin: Coupons ──────────────────────────────────────────────────────


@discount_bp.route("/api/v1/admin/coupons", methods=["GET"])
@require_auth
@require_admin
@require_permission("discount.coupons.view")
def admin_list_coupons():
    """List all coupons."""
    repo = CouponRepository(db.session)
    coupons = repo.find_all()
    return jsonify({"coupons": [c.to_dict() for c in coupons]}), 200


@discount_bp.route("/api/v1/admin/coupons", methods=["POST"])
@require_auth
@require_admin
@require_permission("discount.coupons.manage")
def admin_create_coupon():
    """Create a coupon linked to a discount."""
    data = request.get_json() or {}
    code = data.get("code", "").strip().upper()
    discount_id = data.get("discount_id")

    if not code:
        return jsonify({"error": "Code is required"}), 400
    if not discount_id:
        return jsonify({"error": "discount_id is required"}), 400

    coupon_repo = CouponRepository(db.session)
    if coupon_repo.find_by_code(code):
        return jsonify({"error": f"Coupon '{code}' already exists"}), 400

    discount_repo = DiscountRepository(db.session)
    if not discount_repo.find_by_id(discount_id):
        return jsonify({"error": "Discount not found"}), 404

    coupon = Coupon(
        id=uuid4(),
        code=code,
        discount_id=discount_id,
        max_uses=data.get("max_uses"),
        max_uses_per_user=data.get("max_uses_per_user"),
        is_active=data.get("is_active", True),
        starts_at=data.get("starts_at"),
        expires_at=data.get("expires_at"),
    )
    coupon_repo.save(coupon)
    return jsonify({"coupon": coupon.to_dict()}), 201


@discount_bp.route("/api/v1/admin/coupons/<coupon_id>", methods=["GET"])
@require_auth
@require_admin
@require_permission("discount.coupons.view")
def admin_get_coupon(coupon_id):
    """Get coupon detail."""
    repo = CouponRepository(db.session)
    coupon = repo.find_by_id(coupon_id)
    if not coupon:
        return jsonify({"error": "Coupon not found"}), 404
    return jsonify({"coupon": coupon.to_dict()}), 200


@discount_bp.route("/api/v1/admin/coupons/<coupon_id>", methods=["PUT"])
@require_auth
@require_admin
@require_permission("discount.coupons.manage")
def admin_update_coupon(coupon_id):
    """Update a coupon."""
    repo = CouponRepository(db.session)
    coupon = repo.find_by_id(coupon_id)
    if not coupon:
        return jsonify({"error": "Coupon not found"}), 404

    data = request.get_json() or {}
    if "code" in data:
        coupon.code = data["code"].strip().upper()
    for field_name in ["discount_id", "max_uses", "max_uses_per_user", "is_active", "starts_at", "expires_at"]:
        if field_name in data:
            setattr(coupon, field_name, data[field_name])

    repo.save(coupon)
    return jsonify({"coupon": coupon.to_dict()}), 200


@discount_bp.route("/api/v1/admin/coupons/<coupon_id>", methods=["DELETE"])
@require_auth
@require_admin
@require_permission("discount.coupons.manage")
def admin_delete_coupon(coupon_id):
    """Delete a coupon."""
    repo = CouponRepository(db.session)
    coupon = repo.find_by_id(coupon_id)
    if not coupon:
        return jsonify({"error": "Coupon not found"}), 404
    repo.delete(coupon)
    return jsonify({"message": "Coupon deleted"}), 200


@discount_bp.route("/api/v1/admin/coupons/<coupon_id>/usage", methods=["GET"])
@require_auth
@require_admin
@require_permission("discount.coupons.view")
def admin_coupon_usage(coupon_id):
    """Get coupon usage history."""
    usage_repo = CouponUsageRepository(db.session)
    usages = usage_repo.find_by_coupon(coupon_id)
    return (
        jsonify(
            {
                "usages": [u.to_dict() for u in usages],
                "total": usage_repo.count_by_coupon(coupon_id),
            }
        ),
        200,
    )


@discount_bp.route("/api/v1/admin/coupons/generate", methods=["POST"])
@require_auth
@require_admin
@require_permission("discount.coupons.manage")
def admin_generate_coupons():
    """Bulk generate coupon codes linked to a discount."""
    import random
    import string

    data = request.get_json() or {}
    discount_id = data.get("discount_id")
    count = min(int(data.get("count", 1)), 100)

    if not discount_id:
        return jsonify({"error": "discount_id is required"}), 400

    discount_repo = DiscountRepository(db.session)
    if not discount_repo.find_by_id(discount_id):
        return jsonify({"error": "Discount not found"}), 404

    coupon_repo = CouponRepository(db.session)
    chars = string.ascii_uppercase.replace("O", "").replace("I", "") + "23456789"
    created = []

    for _ in range(count):
        for _attempt in range(10):
            code = "".join(random.choices(chars, k=8))
            if not coupon_repo.find_by_code(code):
                break

        coupon = Coupon(
            id=uuid4(),
            code=code,
            discount_id=discount_id,
            is_active=True,
        )
        coupon_repo.save(coupon)
        created.append(coupon.to_dict())

    return jsonify({"coupons": created, "count": len(created)}), 201
