# USEP Web Project

This is the code that powers the Brown University [U.S. Epigraphy](http://library.brown.edu/projects/usep/) project.

For more information about that project, see that site's ['About' page](http://library.brown.edu/projects/usep/about/)


## Overview

- Framework: Django
- Package manager / command runner: `uv`
- Main app: `usep_app`
- Django settings module: `config.settings`

The site serves:

- collection list and collection detail pages
- inscription pages
- publications pages
- search form and search results
- static database-backed pages such as about, contact, links, and texts

Some page content is rendered directly by Django templates. Inscription and publication content also depends on client-side XML/XSL transforms loaded from configured URLs.


## Configuration

The app requires a repository-adjacent `.env` file. `config/settings.py` loads it at startup and expects environment variables for:

- Django core settings such as debug, admins, allowed hosts, database config, static config, and email
- Solr connection settings
- inscription XML/XSL/SaxonCE URLs
- publication XML/XSL URLs
- a few maintenance URLs used by the app


## Common Commands

Install dependencies:

```bash
uv sync
```

Run the Django development server:

```bash
uv run ./manage.py runserver 127.0.0.1:8000
```

Run database migrations:

```bash
uv run ./manage.py migrate
```

Run tests:

```bash
uv run ./manage.py test
```

---
