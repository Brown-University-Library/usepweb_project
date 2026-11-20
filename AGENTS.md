# AGENTS.md — USEP web project

This file is the source of coding instructions for this repository. Follow it when other repository guides disagree. Keep it within 300 lines, including blank lines and the final horizontal rule. When updating it, shorten repeated guidance first and keep the project index current.

## Contents

- [Project setup and commands](#project-setup-and-commands)
- [Python conventions](#python-conventions)
- [Django views and templates](#django-views-and-templates)
- [Tests and checks](#tests-and-checks)
- [Local work and GitHub](#local-work-and-github)
- [Privacy and publication](#privacy-and-publication)
- [Project index](#project-index)

## Project setup and commands

The project root contains this file, `manage.py`, and `pyproject.toml`. If you start in the enclosing work directory, enter `usepweb_project/` before running commands. Use Python 3.12 for development and checks. Keep new code compatible with the Python minimum declared in `pyproject.toml` (currently 3.10).

| Task | Command from the project root |
| --- | --- |
| Install the locked application dependencies | `uv sync --locked` |
| Start the local Django server | `uv run ./manage.py runserver` |
| List Django management commands | `uv run ./manage.py help` |
| Run the Django test suite | `uv run ./manage.py test` |
| Run one test class | `uv run ./manage.py test usep_app.tests.CollectionViewSortTest` |

- Run standalone Python scripts with `uv run`. For a one-off helper that needs an extra package, use `uv run --no-project --with PACKAGE python SCRIPT ARGS`. Keep temporary helper dependencies out of the application environment and dependency files.
- Django loads `../.env` at startup. Values in that file override matching shell variables. Use `sample.env` to look up the setting names and [README.md](README.md) for local setup.
- In commands intended for older servers, use `grep` or `find`. Local searches can use `rg`.

## Python conventions

- Annotate functions and important variables. Prefer built-in types such as `list[str]` and unions such as `str | None`. Add imports from `typing` or `__future__` only when needed.
- Give standalone scripts a `main() -> None` and an `if __name__ == '__main__':` guard. Let `main()` read arguments and call top-level functions that do the work. Avoid nested function definitions. Keep helper calls shallow, rarely more than three levels below `main()`.
- Prefer a single return when that keeps the function easy to follow. Choose plain names and make checks for missing values explicit.
- Write present-tense docstrings with the opening and closing triple quotes on their own lines. End each non-test function docstring with `Called by: function_name()` and qualify the caller when it lives in another class or module. Start test docstrings with “Checks”. Begin section comments inside functions with `##`.
- For new log messages, label a value with its variable name where practical. Enclose the value in double backticks, as in ```log.debug('result_count, ``%s``', result_count)```.
- The application uses `requests` for existing Solr and XML calls. Reuse that client when maintaining those calls. Prefer `httpx` for new HTTP work where it is installed. It currently belongs to the `local` dependency group. A runtime change that requires it must also account for the application dependencies.
- Follow [ruff.toml](ruff.toml) for formatting, including the 125-character line length and single quotes. Let Markdown paragraphs wrap naturally. For documents with more than three `##` sections, include a linked contents list.

## Django views and templates

- Use function-based views for application endpoints and register them in `config/urls.py`. Most are in `usep_app/views.py`. The search form and results are in `usep_app/search.py`.
- Have views read request parameters, validate input, call the relevant helper, and return a Django response. Place new reusable application logic in `usep_app/libs/`. Prefer helpers that accept plain Python values. Several existing helpers live in `usep_app/models.py`; look there before adding another implementation.
- Prefer CSS for presentation and Django templates or Python for page content. Add JavaScript when the behavior needs to run in the browser. Inscription and publication pages already use browser-side XML transforms, so check the rendered content when changing those pages.

## Tests and checks

- Use Django's test framework. Cover the expected result and at least one meaningful edge case for changed behavior. Run the relevant test first, then the full suite for application changes.
- The existing `usep_app.tests.UrlTest.test_search` queries the configured Solr index. Local development normally reaches it through the tunnel described in the README. Loading the vocabulary template filters can also fetch taxonomy XML. Use sample replies for focused tests that should run independently of these services. Report which checks used sample data and which reached a live service.
- Check every changed Python file with Pylance using the project interpreter and type-checking settings. Use Pyright when Pylance is unavailable. Fix diagnostics with accurate annotations or explicit type checks.
- When linting, first look for Ruff in the project environment and with `command -v ruff`. If needed, locate the installed VS Code Ruff extension's `bundled/libs/bin/ruff`. Run it from the project root with the repository configuration.
- If a check cannot run, report the command, what prevented it from running, and which checks you completed.

## Local work and GitHub

- Start from the user's request and read the surrounding code. Make the smallest change that meets the request, preserve the user's edits, and state any assumption that affects the result. Ask for clarification only when a decision is needed to proceed.
- Local work can begin directly. When the user requests issue-based work, keep each issue focused on one outcome and include its number and a short description in the branch name. Follow the user's branch choice.
- Leave local changes uncommitted for review unless the user explicitly requests a commit for those changes. Treat a push, a pull request, a merge, and closing an identified issue as separate actions requiring authorization. In reports, identify the branch, files changed, checks run, and anything awaiting review.
- For authorized commits, group related changes and use a present-tense message of at most 15 words, such as “Updates search tests”. Keep issues open for the user's review. Use an ordinary reference such as `Refs #123` and check for automatic issue closure before merging.

### Writing issues and comments

- Before an authorized post, read the issue and its comments and follow the latest maintainer direction. Identify Codex visibly as the author or editor of each GitHub issue, pull request description, comment, review, or discussion it writes.
- Begin a new issue description with `Created by Codex at the user's request.` For an issue draft, describe the goal, context, and tasks. Include completion criteria when they help the reader check the outcome.
- When the user supplies an issue body specifically for publication, put their approved text after the attribution and preserve its wording, links, formatting, and order. Keep Codex's interpretation separate. If a redaction is necessary, mark the omission and follow the privacy rules below. For work discussed privately, write a fresh summary for the repository.
- Begin an issue comment with `Codex response` and say whether it is advice, a proposal, an answer, or an implementation report. Distinguish proposals from decisions the user has approved. Post only within the scope the user authorized.
- Use a structured body field or pass multiline text to `gh` with `--body-file`. Read back the posted text, verify its wording and attribution, and share its direct link. If the outcome of a post is uncertain, check for an existing post before retrying.

## Privacy and publication

- Apply these rules to public and private repositories, including tracked files, issues, pull requests, commits, comments, and attachments. Keep private conversation excerpts, raw error emails, logs, tracebacks, configuration values, and sensitive working notes out of repository content.
- Omit server names, hostnames, IP addresses, credentials, cookies, tokens, and private personal or operational details. Use repository-relative paths or variable names in documentation, examples, and agent notes. Keep server-deployment instructions and references to deployment caller scripts outside READMEs.
- Discuss known or suspected security findings privately with the user. Describe repository changes through the general improvement and safe check results. Keep details that identify affected systems or enable exploitation out of repository content.
- Review the exact title, body, links, examples, screenshots, and attachments before posting or editing. Check whether combined details disclose something private. If the authorized content is clearly safe, proceed. If sensitivity is uncertain, show sanitized wording in the private conversation, explain the uncertainty, and wait for confirmation of that exact text.

## Project index

For an overview of how source XML reaches the website and the search index, see [Architecture_overview.md](Architecture_overview.md). The separate data repository maintains the inscriptions and stylesheets. The indexer prepares the published files and updates Solr. This repository serves the Django website.

| Where to look | What it handles |
| --- | --- |
| [config/urls.py](config/urls.py), [usep_app/views.py](usep_app/views.py) | Start with the URL pattern to find the function serving a page. The collection directory and informational pages use the Django database. A collection detail page combines its database description with inscriptions from Solr. |
| [usep_app/search.py](usep_app/search.py), [usep_app/models.py](usep_app/models.py) | Search form and results. `SolrHelper` builds queries and prepares results and filter counts. `Vocab` translates stored codes into display labels using taxonomy XML. |
| [usep_app/usep_templates/](usep_app/usep_templates/), [usep_app/templatetags/](usep_app/templatetags/), [usep_app/static/usep/](usep_app/static/usep/) | Django templates, custom template filters, and static assets. Preserve the capitalization in `collectionS.html` for the directory and `collectioN.html` for one collection. |
| [display_inscription.html](usep_app/usep_templates/display_inscription.html), [publications.html](usep_app/usep_templates/publications.html) | Django supplies the page and resource URLs. Saxon-CE in the browser applies XSL stylesheets to the XML. A page can return HTTP 200 before the browser has loaded the inscription or bibliography. |
| [config/settings.py](config/settings.py), [usep_app/settings_app.py](usep_app/settings_app.py) | Django configuration and application-specific settings for Solr, XML, and stylesheets. |
| [db_transfer_validation.py](usep_app/management/commands/db_transfer_validation.py) | Django command for inspecting schema differences, exporting data, importing into SQLite, and checking the result. Run `uv run ./manage.py db_transfer_validation --help` to list the operations. |
| [Accessibility audit guide](usep_app/libs/a11y/README.md) | Instructions for checking a rendered page with Playwright and axe. The tool uses the `local` dependency group. |

---
