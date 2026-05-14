"""Discount plugin — unified discount & coupon system."""
from vbwd.plugins.base import BasePlugin, PluginMetadata

from plugins.discount.discount.registry import DiscountRuleRegistry

# Module-level registry — other plugins register their rules here
_discount_registry = DiscountRuleRegistry()


class DiscountPlugin(BasePlugin):
    """Unified discount & coupon plugin.

    Provides:
    - Discount rules (percentage, fixed, free shipping, buy-X-get-Y)
    - Coupon codes with usage limits
    - IDiscountRule interface for plugin-specific rules
    - DiscountRuleRegistry for plugin registration
    """

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="discount",
            version="0.1.0",
            description="Unified discount & coupon system",
            author="VBWD",
            dependencies=[],
        )

    def initialize(self, config=None):
        default_config = {
            "max_coupons_per_discount": 100,
            "default_coupon_length": 8,
        }
        merged = {**default_config, **(config or {})}
        super().initialize(merged)

    @property
    def admin_permissions(self):
        return [
            {
                "key": "discount.discounts.view",
                "label": "View discounts",
                "group": "Discounts",
            },
            {
                "key": "discount.discounts.manage",
                "label": "Manage discounts",
                "group": "Discounts",
            },
            {
                "key": "discount.coupons.view",
                "label": "View coupons",
                "group": "Discounts",
            },
            {
                "key": "discount.coupons.manage",
                "label": "Manage coupons",
                "group": "Discounts",
            },
            {
                "key": "discount.configure",
                "label": "Discount settings",
                "group": "Discounts",
            },
        ]

    def on_enable(self):
        # Import models to register with SQLAlchemy
        import plugins.discount.discount.models  # noqa: F401

    def on_disable(self):
        pass

    def get_blueprint(self):
        from plugins.discount.discount.routes import discount_bp

        return discount_bp

    def get_url_prefix(self):
        return ""
