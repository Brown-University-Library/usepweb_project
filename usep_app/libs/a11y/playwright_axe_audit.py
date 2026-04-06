"""
Runs on-demand accessibility audits against a page using Python Playwright and axe.

Called by: main()
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


A11Y_DIR = Path(__file__).resolve().parent
AXE_SCRIPT_PATH = A11Y_DIR / 'axe.min.js'
DEFAULT_AXE_SCRIPT_URL = 'https://unpkg.com/axe-core@4.10.2/axe.min.js'


class A11yAuditError(RuntimeError):
    """
    Represents a failure to execute the Playwright + axe audit.

    Called by: run_axe_audit()
    """


@dataclass
class A11yAuditResult:
    """
    Stores the normalized result returned by the accessibility runner.

    Called by: run_axe_audit()
    """

    url: str
    browser: str
    violation_count: int
    violations: list[dict]

    def to_dict(self) -> dict:
        """
        Builds a JSON-serializable version of the result.

        Called by: main()
        """

        data = {
            'url': self.url,
            'browser': self.browser,
            'violation_count': self.violation_count,
            'violations': self.violations,
        }
        return data


def build_parser() -> argparse.ArgumentParser:
    """
    Builds the CLI parser for the manual a11y audit entrypoint.

    Called by: main()
    """

    parser = argparse.ArgumentParser(description='Audit a page with Python Playwright and axe.')
    parser.add_argument('url', help='Absolute page URL to audit.')
    parser.add_argument(
        '--browser',
        choices=['chromium', 'firefox', 'webkit'],
        default='chromium',
        help='Browser engine used for the audit.',
    )
    parser.add_argument(
        '--wait-until',
        choices=['commit', 'domcontentloaded', 'load', 'networkidle'],
        default='networkidle',
        help='Playwright page load state to await before running axe.',
    )
    parser.add_argument(
        '--timeout-ms',
        type=int,
        default=30000,
        help='Navigation timeout in milliseconds.',
    )
    parser.add_argument(
        '--include-tag',
        action='append',
        default=[],
        help='Optional axe tag filter. Repeat to pass multiple tags.',
    )
    parser.add_argument(
        '--exclude-selector',
        action='append',
        default=[],
        help='Optional CSS selector to exclude from the audit.',
    )
    parser.add_argument(
        '--axe-script-path',
        default=None,
        help='Optional path to a local axe.min.js file.',
    )
    parser.add_argument(
        '--headed',
        action='store_true',
        help='Launch the browser with a visible UI instead of headless mode.',
    )
    return parser


def validate_url(url: str) -> None:
    """
    Validates that the target URL looks runnable before execution.

    Called by: run_axe_audit()
    """

    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise A11yAuditError(f'URL must be absolute. Received: {url}')


def ensure_axe_script(axe_script_path: Path, axe_script_url: str) -> Path:
    """
    Ensures the local axe script exists, downloading it on first use if needed.

    Called by: run_axe_audit()
    """

    if axe_script_path.exists():
        return axe_script_path

    try:
        import httpx
    except ModuleNotFoundError as exc:
        raise A11yAuditError(
            'Downloading axe requires the local dependency group. '
            'Run `uv sync --group local` and retry.'
        ) from exc

    try:
        response = httpx.get(axe_script_url, follow_redirects=True, timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise A11yAuditError(
            f'Unable to download axe from {axe_script_url}. '
            'Pass --axe-script-path to a local axe.min.js file or retry with network access.'
        ) from exc

    axe_script_path.write_text(response.text, encoding='utf-8')
    return axe_script_path


def choose_browser_launcher(playwright_client, browser: str):
    """
    Selects the requested Playwright browser launcher.

    Called by: run_axe_audit()
    """

    browser_map = {
        'chromium': playwright_client.chromium,
        'firefox': playwright_client.firefox,
        'webkit': playwright_client.webkit,
    }
    launcher = browser_map.get(browser)
    if launcher is None:
        raise A11yAuditError(f'Unsupported browser: {browser}')
    return launcher


def build_axe_run_options(include_tags: list[str] | None) -> dict:
    """
    Builds axe run options from the provided include-tag filter.

    Called by: run_axe_audit()
    """

    options = {}
    if include_tags:
        options = {'runOnly': {'type': 'tag', 'values': include_tags}}
    return options


def build_axe_context(exclude_selectors: list[str] | None) -> dict | None:
    """
    Builds the axe context object used to exclude page regions.

    Called by: run_axe_audit()
    """

    context = None
    if exclude_selectors:
        context = {
            'exclude': [[selector] for selector in exclude_selectors],
        }
    return context


def evaluate_axe(page, include_tags: list[str] | None, exclude_selectors: list[str] | None) -> dict:
    """
    Runs axe in the current page and returns the raw audit result.

    Called by: run_axe_audit()
    """

    context = build_axe_context(exclude_selectors)
    options = build_axe_run_options(include_tags)
    result = page.evaluate(
        """async ({ context, options }) => {
            return await window.axe.run(context, options);
        }""",
        {'context': context, 'options': options},
    )
    return result


def normalize_violations(violations: list[dict]) -> list[dict]:
    """
    Normalizes axe violations into a stable JSON-friendly shape.

    Called by: run_axe_audit()
    """

    normalized_violations = []
    for violation in violations:
        nodes = []
        for node in violation.get('nodes', []):
            nodes.append(
                {
                    'html': node.get('html'),
                    'target': node.get('target', []),
                    'failure_summary': node.get('failureSummary', ''),
                }
            )

        normalized_violations.append(
            {
                'id': violation.get('id'),
                'impact': violation.get('impact') or 'unknown',
                'description': violation.get('description'),
                'help': violation.get('help'),
                'help_url': violation.get('helpUrl'),
                'tags': violation.get('tags', []),
                'nodes': nodes,
            }
        )

    return normalized_violations


def run_axe_audit(
    url: str,
    browser: str = 'chromium',
    wait_until: str = 'networkidle',
    timeout_ms: int = 30000,
    include_tags: list[str] | None = None,
    exclude_selectors: list[str] | None = None,
    headless: bool = True,
    axe_script_path: str | None = None,
    axe_script_url: str = DEFAULT_AXE_SCRIPT_URL,
) -> A11yAuditResult:
    """
    Executes a Python Playwright + axe audit and returns normalized output.

    Called by: main()
    """

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        raise A11yAuditError(
            'Playwright is not installed. Run `uv sync --group local` and '
            '`uv run --group local playwright install chromium` before using this tool.'
        ) from exc

    validate_url(url)
    resolved_axe_script_path = Path(axe_script_path) if axe_script_path else AXE_SCRIPT_PATH
    axe_file_path = ensure_axe_script(resolved_axe_script_path, axe_script_url)

    try:
        with sync_playwright() as playwright_client:
            launcher = choose_browser_launcher(playwright_client, browser)
            browser_instance = launcher.launch(headless=headless)
            page = browser_instance.new_page()
            try:
                page.goto(url, timeout=timeout_ms, wait_until=wait_until)
                page.add_script_tag(path=axe_file_path)
                raw_result = evaluate_axe(
                    page=page,
                    include_tags=include_tags,
                    exclude_selectors=exclude_selectors,
                )
            finally:
                page.close()
                browser_instance.close()
    except PlaywrightError as exc:
        raise A11yAuditError(
            'Accessibility audit failed. Run `uv sync --group local` and '
            '`uv run --group local playwright install chromium` before using this tool.'
        ) from exc

    violations = normalize_violations(raw_result.get('violations', []))
    result = A11yAuditResult(
        url=url,
        browser=browser,
        violation_count=len(violations),
        violations=violations,
    )
    return result


def main() -> None:
    """
    Parses CLI arguments, runs the audit, and prints the JSON result.

    Called by: N/A
    """

    parser = build_parser()
    args = parser.parse_args()
    result = run_axe_audit(
        url=args.url,
        browser=args.browser,
        wait_until=args.wait_until,
        timeout_ms=args.timeout_ms,
        include_tags=args.include_tag,
        exclude_selectors=args.exclude_selector,
        headless=(not args.headed),
        axe_script_path=args.axe_script_path,
    )
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == '__main__':
    main()
