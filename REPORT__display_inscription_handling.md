# `display_inscription()` handling analysis

## Prompt

Goal: Analyze how this project's html is rendered.

Context:

- Most Django projects I've worked on receive a user-request for a resource, prepare the data (typically from a solr-query or a db-queery), and send the data through a django template.

- Ive worked on a couple of projects, though, where there is xml-data stored in github, and a an xslt-stylesheet stored in github, and the python code in the django project processes the xml-data with the xslt-stylesheet to produce html. That html is then included into the template to produce the final html sent to the browser.

Task:

- review the `usepweb_project/usep_app/views.py` to get an overview of the calls made to this webapp.

- review the `usepweb_project/usep_app/views.py` function `display_inscription()` to get a more specific sense of how inscription-pages are displayed.

- follow all code-calls in that view-function to understand each step of how data is gathered, and processed, and returned to the user's browser.

- save the analysis to `usepweb_project/REPORT__display_inscription_handling.md` 

- save this prompt to `usepweb_project/TMP__prompt.md`


## Scope

This report reviews:

- `usepweb_project/usep_app/views.py` at a high level
- the specific `display_inscription()` view
- the helper calls and template behavior that together produce the inscription page HTML

## High-level overview of how this project renders HTML

This project uses **more than one rendering pattern**.

- **Standard Django server-side rendering**
  - Several views gather data in Python and call `render()` with a Django template.
  - Examples:
    - `collections()`
    - `collection()`
    - `publications()`
    - `pub_children()`
    - `texts()`, `links()`, `about()`, `contact()`

- **Client-side XML + XSLT rendering for inscription pages**
  - `display_inscription()` does **not** fetch or transform inscription XML into final HTML on the server.
  - Instead, the Django view builds a small context containing URLs and identifiers.
  - Django renders a shell template: `usep_templates/display_inscription.html`.
  - In the browser, JavaScript loads:
    - the source inscription XML
    - an intermediate XSLT (`xipr_url`)
    - a final display XSLT (`xsl_url`)
    - the Saxon-CE processor
  - The browser performs the XSLT transforms and injects the resulting HTML into the page.

So for inscription pages, Django is primarily acting as a **URL/context assembler plus HTML shell renderer**, while the final inscription content is rendered **client-side**.

## Overview of `views.py`

`config/urls.py` maps incoming URLs into view functions in `usep_app/views.py`.

### URL mappings in `config/urls.py`

Relevant routes:

- `/usep/collections/` -> `views.collections`
- `/usep/collections/<collection>/` -> `views.collection`
- `/usep/inscription/<inscription_id>/` -> `views.display_inscription`
- `/usep/publications/` -> `views.publications`
- `/usep/publication/<publication>/` -> `views.pub_children`
- `/usep/texts/` -> `views.texts`
- `/usep/links/` -> `views.links`
- `/usep/about/` -> `views.about`
- `/usep/contact/` -> `views.contact`
- `/usep/search/` and `/usep/search/results/` -> search views in `usep_app/search.py`
- `/usep/version/` -> `views.info`
- `/usep/error_check/` -> `views.error_check`
- `/usep/admin/links/` -> `views.admin_links`

### What each main view does

- **`info()`**
  - Returns JSON version/commit metadata.
  - No HTML template rendering.

- **`error_check()`**
  - Raises an error in debug mode to test admin error emails.
  - Otherwise returns a 404-style response.

- **`collections()`**
  - Reads `FlatCollection` objects from the database.
  - Builds a Python dictionary for regions and collections.
  - Returns either JSON/JSONP or renders `usep_templates/collectionS.html`.

- **`collection()`**
  - Uses `models.Collection()` to query Solr.
  - Enriches Solr data and combines it with `FlatCollection` metadata from the database.
  - Returns either JSON/JSONP or renders `usep_templates/collectioN.html`.

- **`display_inscription()`**
  - Does not query Solr or the database for inscription display data.
  - Builds URLs needed for the browser to fetch XML/XSLT resources.
  - Returns either JSON context or renders `usep_templates/display_inscription.html`.

- **`publications()`**
  - Prepares URLs to bibliography XML and publication XSL.
  - Adjusts hostnames when needed.
  - Renders `usep_templates/publications.html`.

- **`pub_children()`**
  - Fetches bibliography XML from a remote URL.
  - Parses the XML server-side with `lxml` to find a title.
  - Uses `models.Publication()` to query Solr and build inscription lists.
  - Returns JSON/JSONP or renders `usep_templates/publicatioN.html`.

- **`texts()`, `links()`, `about()`, `contact()`**
  - Fetch single-record page content from the database.
  - Render `usep_templates/static.html`.

## Detailed analysis of `display_inscription()`

Source location:

- `usepweb_project/usep_app/views.py`

Function body summary:

1. Log start time.
2. Instantiate `DisplayInscriptionHelper` from `models.py`.
3. Build a URL for the inscription XML.
4. Build a context dictionary containing all browser-needed URLs.
5. If `?format=json`, return that context as JSON.
6. Otherwise render `usep_templates/display_inscription.html`.

### Actual code path

```text
HTTP request
  -> Django URL resolver (`config/urls.py`)
  -> `views.display_inscription(request, inscription_id)`
  -> `DisplayInscriptionHelper.build_source_xml_url(...)`
  -> `DisplayInscriptionHelper.build_context(...)`
  -> `render(request, 'usep_templates/display_inscription.html', context)`
  -> browser receives HTML shell with JS and URLs
  -> browser loads XML/XSL resources
  -> Saxon-CE runs XSLT in the browser
  -> transformed HTML is injected into the DOM
```

## Step-by-step trace of `display_inscription()`

### 1. Route dispatch

`config/urls.py` contains:

```python
re_path(r'^usep/inscription/(?P<inscription_id>[^/]+)/$', views.display_inscription, name='inscription_url')
```

This means a request like:

```text
/usep/inscription/ABCD123/
```

calls:

```python
display_inscription(request, inscription_id='ABCD123')
```

### 2. View starts and creates helper

In `views.py`:

```python
display_inscription_helper = DisplayInscriptionHelper()
```

This helper lives in `usep_app/models.py`. It is not a Django model backed by a database table here; it is just a utility class used to assemble URLs and context.

### 3. Source XML URL is built

The view calls:

```python
source_xml_url = display_inscription_helper.build_source_xml_url(
    settings_app.DISPLAY_INSCRIPTION_XML_URL_PATTERN,
    request.is_secure(),
    request.get_host(),
    inscription_id
)
```

#### Inputs involved

- `settings_app.DISPLAY_INSCRIPTION_XML_URL_PATTERN`
  - Comes from environment variable `USEPWEB__DISPLAY_INSCRIPTION_XML_URL_PATTERN`
- `request.is_secure()`
  - Determines whether to use `http` or `https`
- `request.get_host()`
  - Current host serving the request
- `inscription_id`
  - Captured from the URL

#### What `build_source_xml_url()` does

In `models.py`:

```python
def build_source_xml_url(self, url_pattern, is_secure, hostname, inscription_id):
    scheme = 'https' if (is_secure == True) else 'http'
    url = url_pattern.replace('SCHEME', scheme)
    url = url.replace('HOSTNAME', hostname)
    url = url.replace('INSCRIPTION_ID', inscription_id)
    return url
```

Important observations:

- The URL is generated by string substitution.
- `hostname` is accepted as an argument but is only used if the configured pattern contains `HOSTNAME`.
- No XML is fetched here.
- No transformation happens here.
- The result is simply a browser-usable URL pointing to the inscription XML source.

### 4. Context is built for the template

The view then calls:

```python
context = display_inscription_helper.build_context(
    request.get_host(),
    project_settings.STATIC_URL,
    inscription_id,
    source_xml_url,
    settings_app.DISPLAY_INSCRIPTION_XSL_URL,
    settings_app.DISPLAY_INSCRIPTION_SAXONCE_FILE_URL,
    settings_app.DISPLAY_INSCRIPTION_XIPR_URL
)
```

#### Inputs involved

- `request.get_host()`
- `project_settings.STATIC_URL`
- `inscription_id`
- `source_xml_url` from the previous step
- `settings_app.DISPLAY_INSCRIPTION_XSL_URL`
  - Environment variable `USEPWEB__DISPLAY_INSCRIPTION_XSL_URL`
- `settings_app.DISPLAY_INSCRIPTION_SAXONCE_FILE_URL`
  - Environment variable `USEPWEB__DISPLAY_INSCRIPTION_SAXONCE_FILE_URL`
- `settings_app.DISPLAY_INSCRIPTION_XIPR_URL`
  - Environment variable `USEPWEB__DISPLAY_INSCRIPTION_XIPR_URL`

#### What `build_context()` does

In `models.py`:

```python
def build_context(self, hostname, custom_static_url, inscription_id, source_xml_url, xsl_url, saxonce_url, xipr_url):
    context = {
      'custom_static_url': self.update_host(hostname, custom_static_url),
      'inscription_id': inscription_id,
      'source_xml_url': self.update_host(hostname, source_xml_url),
      'xsl_url': self.update_host(hostname, xsl_url),
      'saxonce_file_url': self.update_host(hostname, saxonce_url),
      'xipr_url': self.update_host(hostname, xipr_url)
      }
    return context
```

So Django passes the template only these values:

- `custom_static_url`
- `inscription_id`
- `source_xml_url`
- `xsl_url`
- `saxonce_file_url`
- `xipr_url`

#### What `update_host()` does

```python
def update_host(self, hostname, url):
    if hostname.lower() == 'usepigraphy.brown.edu':
        url = url.replace('library.brown.edu', 'usepigraphy.brown.edu')
    return url
```

This is a host-rewriting compatibility layer.

Implications:

- If the request host is `usepigraphy.brown.edu`, URLs that point at `library.brown.edu` are rewritten.
- This affects static assets, XML URL, XSL URL, Saxon-CE file URL, and `xipr_url`.
- This logic exists to keep browser-side AJAX/resource loading working under multiple hostnames.

### 5. The view returns either JSON or a template

The final branch in `display_inscription()` is:

```python
if request.GET.get('format', '') == 'json':
    resp = HttpResponse(json.dumps(context, sort_keys=True, indent=2), content_type='application/javascript; charset=utf-8')
else:
    resp = render(request, 'usep_templates/display_inscription.html', context)
```

So there are two response modes:

- **JSON mode**
  - `?format=json`
  - Returns only the context dictionary
  - Useful for debugging or inspection

- **HTML mode**
  - Default behavior
  - Renders `display_inscription.html`

## What the Django template actually does

Template:

- `usepweb_project/usep_app/usep_templates/display_inscription.html`

This template is a **page shell**, not the final inscription content itself.

### Server-rendered portions of the template

Django directly renders:

- page title using `{{ inscription_id }}`
- loading indicator background URL via `{{ custom_static_url }}`
- `<script src="{{ saxonce_file_url }}">`
- Highslide and other static asset URLs via `{{ custom_static_url }}`
- JavaScript variables containing:
  - `{{ source_xml_url }}`
  - `{{ xipr_url }}`
  - `{{ xsl_url }}`

The server-rendered body content is initially just:

- `<div id="loading">`
- `<div id="container"></div>`
- `<div id="images"></div>`

That means the inscription body content is **not yet present** when Django sends the response.

## How the browser builds the final inscription HTML

The critical browser-side code is the `onSaxonLoad` function in `display_inscription.html`.

### Client-side transformation steps

Inside the template JavaScript:

```javascript
var onSaxonLoad = function() {
    var inscription_xml = "{{ source_xml_url }}"
    var xsl = Saxon.requestXML("{{ xipr_url }}");
    var xml = Saxon.requestXML(inscription_xml);
    var proc = Saxon.newXSLT20Processor(xsl);

    var xml2 = proc.transformToDocument(xml);
    var xsl2 = Saxon.requestXML("{{ xsl_url }}");
    var proc2 = Saxon.newXSLT20Processor(xsl2);

    proc2.updateHTMLDocument(xml2);
    proc2.setSuccess(fade("out", document.getElementById("loading")));
};
```

### Meaning of each step

- **Load source inscription XML**
  - `Saxon.requestXML(inscription_xml)` fetches the inscription XML document from `source_xml_url`.

- **Load first XSLT: `xipr_url`**
  - `Saxon.requestXML("{{ xipr_url }}")`
  - This appears to be an intermediate transformation step.

- **Run first transformation**
  - `proc.transformToDocument(xml)` converts the original XML into a transformed intermediate XML document named `xml2`.

- **Load second XSLT: `xsl_url`**
  - `Saxon.requestXML("{{ xsl_url }}")`
  - This is the display stylesheet.

- **Run second transformation into the live page**
  - `proc2.updateHTMLDocument(xml2)` applies the second XSLT and updates the current browser DOM.

### Conclusion about the rendering architecture

For inscription pages, the final page content is produced by a **two-stage client-side XSLT pipeline**:

```text
source inscription XML
  -> transform with xipr.xsl-equivalent (`xipr_url`)
  -> intermediate XML document
  -> transform with display XSL (`xsl_url`)
  -> HTML inserted into browser document
```

This matches the architecture you described from other projects much more closely than standard Django server-side templating.

## What is and is not happening on the server

### What the server does

- Receives the URL request.
- Extracts `inscription_id`.
- Builds resource URLs from environment-backed settings.
- Adjusts hostnames when needed.
- Renders a Django template containing placeholders and JavaScript.
- Returns the HTML shell response.

### What the server does not do in `display_inscription()`

- It does **not** fetch the inscription XML itself.
- It does **not** parse the inscription XML in Python.
- It does **not** apply XSLT in Python.
- It does **not** generate the final inscription HTML on the server.
- It does **not** query Solr or the database for inscription body content.

## Data sources involved in inscription-page display

### 1. Environment variables / app settings

From `usep_app/settings_app.py`:

- `DISPLAY_INSCRIPTION_XML_URL_PATTERN`
- `DISPLAY_INSCRIPTION_XSL_URL`
- `DISPLAY_INSCRIPTION_SAXONCE_FILE_URL`
- `DISPLAY_INSCRIPTION_XIPR_URL`

These determine where the browser will fetch:

- the inscription XML
- the intermediate XSLT
- the display XSLT
- the Saxon-CE processor script

### 2. Django static files

The template also references static assets such as:

- CSS files
- loading image
- Highslide JS/CSS
- fade helper JS

### 3. Remote XML/XSLT resources

The actual inscription content depends on remote resources fetched by the browser:

- source XML from `source_xml_url`
- XSLT from `xipr_url`
- XSLT from `xsl_url`

## Request/response lifecycle for an inscription page

### End-to-end lifecycle

1. User requests `/usep/inscription/<inscription_id>/`.
2. Django routes the request to `display_inscription()`.
3. `display_inscription()` computes:
   - source XML URL
   - stylesheet URLs
   - Saxon-CE URL
   - adjusted static URL
4. Django renders `display_inscription.html` with those values.
5. Browser loads the returned HTML shell.
6. Browser loads Saxon-CE and supporting JS/CSS.
7. Browser fetches inscription XML and XSLT resources.
8. Browser performs two XSLT transforms.
9. Resulting HTML is injected into the live document.
10. User sees the final inscription page.

## Comparison with the other rendering patterns in this app

This app is mixed-mode:

- **Collections / publication-list / static pages**
  - Mostly server-side Django rendering, often with Python-prepared data.

- **Inscription pages**
  - Server delivers a lightweight wrapper page.
  - Browser performs the expensive/content-specific rendering.

- **Publications page**
  - It also appears to lean toward XML/XSL-based rendering through URLs passed into the template, though this report focused on inscription pages.

## Key findings

- `display_inscription()` is intentionally thin.
- The important work is not in Python transformation logic.
- The Python side only computes and exposes resource locations.
- The actual inscription HTML is produced in the browser using **Saxon-CE** and **two XSLT transforms**.
- The inscription-page rendering pipeline therefore depends heavily on external XML/XSL resources and browser-side JavaScript execution.

## Practical answer to the original question

If you want to know how inscription HTML is rendered in this project, the answer is:

- Django receives the inscription request and renders a shell template.
- That template contains JavaScript plus URLs to XML and XSLT resources.
- The browser then fetches the XML and XSLT files and transforms the XML into HTML client-side.
- So the final inscription HTML is **not** rendered directly by Django templates from Python data structures in the usual way.

## Most important files for this behavior

- `usepweb_project/config/urls.py`
- `usepweb_project/usep_app/views.py`
- `usepweb_project/usep_app/models.py` (`DisplayInscriptionHelper`)
- `usepweb_project/usep_app/settings_app.py`
- `usepweb_project/usep_app/usep_templates/display_inscription.html`

## Suggested next follow-up if needed

If you want an even deeper trace beyond this report, the next files/resources to inspect would be:

- the concrete environment-variable values for the inscription XML/XSL URLs
- the XSLT file located at `DISPLAY_INSCRIPTION_XIPR_URL`
- the XSLT file located at `DISPLAY_INSCRIPTION_XSL_URL`
- the actual XML returned for a sample inscription URL

Those would show exactly how the XML structure is converted into the final DOM/HTML visible in the browser.
