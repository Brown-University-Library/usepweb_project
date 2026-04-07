› Goal:

  Fix django-related accessibility errors.

  Context:

  - For inscription pages, much of the content is built from applying an xml stylesheet to inscription xml. We're ignoring all a11y errors in stylesheet-built html.

  - For other pages, we do want to fix the a11y errors.

  - The example pages we want fixed:
  	- Collections page: <http://127.0.0.1:8000/usep/collections/>
  	- Collection page (example): <http://127.0.0.1:8000/usep/collections/CA.Berk.UC.HMA/>
  	- Inscription page (example): <http://127.0.0.1:8000/usep/inscription/CA.Berk.UC.HMA.G.8-3898/>
  	- Also check the search, publications, about, and contact pages.

  - Hopefully some fixes to base templates will improve multiple pages.

  Tasks:

  - Review `usepweb_project/AGENTS.md` for code-directives.
    - Due to this project being old, it is using a non-standard older version of django, and does not have a run_tests.py script.

  - Run the new accessibility-checker on the specified pages if possible.

  - For color-contrast errors, make small changes and re-test.

  - Make changes to appropriate base-templates where possible.

  - Avoid trying to fix html issues on inscription-pages where the html is created by stylesheets. Examine any code you need to in order to determine if failing accessibility is due to django, not stylesheet-created html.

  - When finished with a page, pause so I can review and commit changes.

  ---


Agent notes:

- Current pages addressed cleanly:

  - collections list page
  - collection detail page
  - inscription page loading indicator
  - search form
  - search results
  - about/contact header and static-content issues

  I kept the fixes repo-local to templates and static assets, and stopped short of stylesheet-generated inscription HTML except where the loading UI was clearly in repo-controlled Highslide assets.

- Use the local a11y checker with:

  `uv run --group local ./usep_app/libs/a11y/playwright_axe_audit.py <url>`

  On this machine, `webkit` is the working default. `chromium` has been observed to crash at launch.

- For reliable verification, start a fresh django server on a new port, for example:

  `uv run ./manage.py runserver 127.0.0.1:8001`

  The long-running `:8000` dev server may serve stale template/CSS state during iterative a11y work.

- WAVE may misread contrast when text is visually sitting on a dark background supplied only by a background image. The header `About | Contact` issue was fixed by giving the text-link row its own explicit dark background in the DOM/CSS, rather than relying on the header image alone.

- The static pages (`about`, `contact`, etc.) render database-driven HTML through `usep_app/usep_templates/static.html`. For a11y work there, prefer wrapping or styling the shared template/container instead of assuming the content is hard-coded in a page template.

- The search-results page layout is sensitive to markup changes. Keeping the existing `ul#facets` hook preserved the original float/right-column layout and typography. Avoid replacing that outer list element unless you also update the page-specific CSS accordingly.

- For inscription pages, repo-controlled accessibility fixes currently include the header/base-template work plus Highslide assets used around the XSLT output. Avoid trying to clean up XSLT-generated inscription body HTML in the django session unless the issue is clearly in repo-controlled non-XSLT markup or assets.

---
