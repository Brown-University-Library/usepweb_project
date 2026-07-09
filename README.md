# USEP Web Project

This is the code that powers the Brown University [U.S. Epigraphy](http://library.brown.edu/projects/usep/) project.

For more information about that project, see that site's ['About' page](http://library.brown.edu/projects/usep/about/)


## Contents

- [Overview](#overview)
- [Configuration](#configuration)
- [Localbox installation for devs](#localbox-installation-for-devs)
- [Usage](#usage)
- [Misc](#misc)


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


## Localbox installation for devs

- get the code

    ```bash
    mkdir ./usepweb_project_stuff
    cd ./usepweb_project_stuff
    git clone `git@github.com:Brown-University-Library/usepweb_project.git`
    ```

- set up the venv

    ```bash
    cd ./usepweb_project
    uv sync
    ```

- set up the dotenv file

    Get a copy of the `.env` file from a developer and put it in the `./usepweb_project_stuff/` directory.

## Usage

### Initial

- set up an SSH tunnel to Solr

    (Assumes Solr is locked down to only allow access from a dev or prod server via IP.)

    In a separate terminal tab, run:

    ```bash
    ssh -N -L 9999:solr-server.domain.edu:1234 username@dev-server.domain.edu
    ```

    - The `-N` flag tells SSH not to run a remote command, appropriate because we're just port-forwarding.
    - The `-L 9999:solr-server.domain.edu:1234` flag forwards local port `9999` through `dev-server.domain.edu` to Solr at `solr-server.domain.edu:1234`.

    This, then, allows you to make a `.env` setting like `USEPWEB__SOLR_URL_BASE="http://127.0.0.1:9999/solr-root/select/"`.

    Running that `ssh` command won't show any output, but you can confirm the tunnel is working by opening `http://127.0.0.1:9999/solr/#/` in a browser.

    That connection will stay open as long as the terminal tab is open.

- Run the development server

    ```bash
    uv run ./manage.py runserver 
    ```

- Run database migrations (one-time; initial setup)

    ```bash
    uv run ./manage.py migrate
    ```

- Run tests

    ```bash
    uv run ./manage.py test
    ```

### General work

- start the ssh-tunnel
- start the server via runserver
- test as needed


## Misc

- Database transfer/export/import support is available via `uv run ./manage.py db_transfer_validation --help`.
  See the docstring in `usep_app/management/commands/db_transfer_validation.py` for purpose and usage notes.


---
