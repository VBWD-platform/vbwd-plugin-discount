# vbwd-plugin-discount

> VBWD backend discount plugin

**Type:** Backend plugin · **Host app:** `vbwd-backend` · **Plugin:** `discount`

Part of the [VBWD platform](https://github.com/VBWD-platform). This repository is one
plugin in the modular VBWD SaaS marketplace platform; the core is intentionally
agnostic and gains this functionality only when the plugin is enabled.

## Install

Clone into the backend plugin directory and enable it:

```bash
git clone https://github.com/VBWD-platform/vbwd-plugin-discount.git vbwd-backend/plugins/discount
```

Then register it in `plugins/plugins.json` (`"discount": { "enabled": true }`)
and add any config to `plugins/config.json`. The plugin follows the standard
layered layout (`routes` → `services` → `repositories` → `models`) and exposes
a `BasePlugin` subclass in `__init__.py`.

## Versioning & changelog

Releases are tagged (e.g. `v26.6`); see [`CHANGELOG.md`](./CHANGELOG.md).

## License

Business Source License 1.1 — see [`LICENSE`](./LICENSE). Free for commercial
use while annual VBWD-attributable sales stay below the value of 6.7 BTC for the
reporting year; above that, a commercial license is required.

## Documentation

Full platform documentation lives at **[vbwd.cc/docs](https://vbwd.cc/docs)**.

- [Plugin system](https://vbwd.cc/docs-plugin-system) — how backend plugins are registered, enabled, and configured
- [Discounts](https://vbwd.cc/docs-core-discount) — documentation for this plugin's domain
- [Architecture](https://vbwd.cc/docs-architecture) — platform layering and the core-agnosticism rule
- [Getting started](https://vbwd.cc/docs-getting-started) — install a VBWD instance and enable plugins
