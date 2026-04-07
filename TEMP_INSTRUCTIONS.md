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
