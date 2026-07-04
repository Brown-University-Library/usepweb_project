# USEP Web Project

This is the code that powers the Brown University [U.S. Epigraphy](http://library.brown.edu/projects/usep/) project.

For more information about that project, see that site's ['About' page](http://library.brown.edu/projects/usep/about/)


## Contents

- [Overview](#overview)
- [Configuration](#configuration)
- [Localbox installation for devs](#localbox-installation-for-devs)
- [Usage](#usage)


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


---
