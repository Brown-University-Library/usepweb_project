# Accessibility Audit Tool

This directory contains a Python Playwright + axe runner for manual accessibility checks.


## Usage

From the project root:

```bash
uv run --group local ./usep_app/libs/a11y/playwright_axe_audit.py http://127.0.0.1:8000/usep/
```

Optional flags:

- `--browser chromium|firefox|webkit`
- `--wait-until commit|domcontentloaded|load|networkidle`
- `--timeout-ms 30000`
- `--include-tag wcag2a`
- `--exclude-selector .skip-this-region`
- `--axe-script-path /path/to/axe.min.js`
- `--headed`

This tool is not wired into Django's normal test discovery, so GitHub CI should not run it unless explicitly configured to do so.


## Initial setup

Install the local dependency group and a Playwright browser binary:

```bash
uv sync --group local
uv run --group local playwright install webkit
```

If you want Chromium instead, install it and pass `--browser chromium` explicitly:

```bash
uv run --group local playwright install chromium
uv run --group local ./usep_app/libs/a11y/playwright_axe_audit.py --browser chromium http://127.0.0.1:8000/usep/
```
