# USEP: project architecture and data flow

October 23, 2026.

Below is a description of the flow of USEP work -- and an overview of the current architecture.


## Contents

- [Data-flow overview](#data-flow-overview)
- [The main parts of the architecture](#the-main-parts-of-the-architecture)
- [How the website builds a page](#how-the-website-builds-a-page)
- [What the indexer prepares](#what-the-indexer-prepares)
- [Where maintainers can start](#where-maintainers-can-start)
- [Update timing and failures](#update-timing-and-failures)


## Data-flow overview

1. **An editor pushes a change to GitHub.** The change might add an inscription, correct its description or transcription, change the bibliography or stylesheets, or remove a file.
2. **GitHub sends a webhook message to the USEP "listener/indexer".** This is an HTTP notice about the push. It contains info about files that were added, modified, and removed.
3. **The listener saves an update file.** It writes a JSON file to a folder of waiting work. (The code calls this folder the *spool*.) The listener then responds with an "ok" to GitHub. It doesn't pull source files or update Solr during that request.
4. **A cron job reads waiting work.** The cron job calls processor code that first gathers waiting work from one or more JSON files.
5. **The processor code pulls and copies current source data.** It runs a Git pull in the server's local `usep-data` directory, gathers the inscription folders into one public folder, and copies other `usep-data` files. It adjusts links to the bibliography and other XML reference files in the published copies.
6. **The processor code then indexes updated information.** For inscription changes, it builds complete records locally, checks them, and sends them to Solr. Removed inscriptions are deleted from Solr when no corresponding public XML file remains.
7. **Readers see the new content.** When a user loads an inscription webpage after the steps above, the webpage uses the updated public XML; searches and inscription lists use the updated Solr records.


## The main parts of the architecture

(Note the links to the four USEP GitHub repos.)

| Part | Info |
| --- | --- |
| [`usep-data`](https://github.com/Brown-University-Library/usep-data) | Contains all the XML inscriptions in EpiDoc format, as well as XSL stylesheets and CSS used by the webapp. |
| [`usep_indexer_project`](https://github.com/Brown-University-Library/usep_indexer_project) | The "listener/indexer" webapp. It receives GitHub notices, saves work to files, prepares public XML/resources, and updates Solr. |
| Solr | The search service. It holds records derived from the XML for searching text, filtering results, and listing inscriptions. |
| [`usepweb_project`](https://github.com/Brown-University-Library/usepweb_project) | The Django website. It handles page requests, queries Solr, reads its own database, and supplies page templates and file URLs to the browser. It contains a database for collection descriptions and generally unchanging page content (such as the "About" and "Contact" pages). |
| [`usep-images`](https://github.com/Brown-University-Library/usep-images) | Image files referenced by the inscription data. This is a data repository, not an application. A cron-job runs a git-pull once-an-hour. |
| User's browser | Shows the Django page and, for inscription details, uses Saxon-CE JavaScript to turn XML and XSL into visible HTML content on the fly. It also displays images. |


---

## How the website builds a page

There are several sources of page content. 

| What a reader opens | Where the content comes from |
| --- | --- |
| Collection directory ([link](https://library.brown.edu/projects/usep/collections/)) | The website database supplies the collection entries. |
| A collection’s inscription list ([link](https://library.brown.edu/projects/usep/collections/RI.Prov.BU/)) | Solr supplies the inscriptions; the website database supplies the collection description. |
| Search form and results ([link](https://library.brown.edu/projects/usep/search/)) | Django queries Solr for available filters and matching records. XML lists of terms help turn stored codes into readable labels. |
| An inscription page ([link](https://library.brown.edu/projects/usep/inscription/RI.Prov.BU.G.21.04.01-mdn/)) | Django supplies the surrounding page and file URLs. Saxon-CE in the browser reads the inscription XML, pulls in bibliography entries and other details from separate XML files, and applies XSL instructions to build the detailed display. |
| Publications directory ([link](https://library.brown.edu/projects/usep/publications/)) | The browser uses XSL to turn the project's bibliography XML file (`titles.xml`) into a publications list. A particular publication’s inscription list uses Solr. |
| About, Contact, Links, and Texts ([link](https://library.brown.edu/projects/usep/about/)) | Django reads the website database and renders templates. |
| Images ([link](https://library.brown.edu/usep_images/RI.Prov.BU.G.21.04.01-mdn-Det1.jpg)) | The browser follows image references to published USEP image files or external image URLs. |


## What the indexer prepares

### Public files

The source inscriptions are organized under `xml_inscriptions/bib_only/`, `xml_inscriptions/metadata_only/`, and `xml_inscriptions/transcribed/`. The processor gathers them into one public `inscriptions/` folder. If the same filename occurs in more than one source folder, the transcribed version takes precedence over metadata-only, which takes precedence over bibliography-only.

The processor also copies `resources/`, including bibliography and XSL files. 

### Search records

For each inscription being updated, the index-code called by the processor:

1. Parses the XML and applies the configured XSL instructions to build the initial search record.
2. Adds the complete set of bibliography references and searchable transcription text.
3. Records the first usable image reference for search/list thumbnails. The source XML retains all image references for the detail display.
4. Checks required values and prepares one complete record before sending it to Solr.

An ordinary one-inscription update sends one complete record rather than several separate updates for its different parts. Multiple inscription-updates are fully prepared ahead of time, and then batch-sent to solr for more speed and efficiency.

### Small updates and full rebuilds

| Change | What happens |
| --- | --- |
| Inscription added or edited | Update the affected inscription’s Solr record from the inscription's current XML. |
| Inscription moved between the three source folders | Check the resulting public filename and update it if a copy remains. A folder move need not mean deleting the inscription. |
| Inscription removed entirely | Remove it from all Django displays and delete its Solr record. |
| The bibliography XML file (`titles.xml`) changed, or XSL used to build search records changed | Rebuild all search records, because many inscriptions may be affected. The code also checks XSL files included by those instructions. |
| Resource used only for display changed | Make the XSL file active so the browser uses it when displaying a detailed inscription. |
| Full rebuild requested | Pull and copy current data, attempt every inscription, send records in groups, and remove Solr records that no longer have a source file. (Solr records are only removed if no inscription failed.) |

Both ordinary processing and full rebuilding refresh the public files. 


## Where maintainers can start

This is for figuring out what code affects what function. Paths are relative to the named repository. These are some useful pointers, not a complete file inventory.

| Area | Files and functions |
| --- | --- |
| Indexer request handling | `config/urls.py`; `usep_indexer_app/views.py`, especially `handle_github_push()` |
| Read GitHub notices | `usep_indexer_app/lib/payloads.py` |
| Save and process waiting work | `usep_indexer_app/lib/spool.py`; `usep_indexer_app/management/commands/process_spool.py` |
| Pull source data and prepare public files | `usep_indexer_app/lib/processor.py`: `prepare_public_data()`, `copy_files()`, `process_incremental()` |
| Build and check search records | `usep_indexer_app/lib/indexer.py`: `build_complete_document()`; `bibliography.py`; `transcription.py` |
| Send updates to Solr | `usep_indexer_app/lib/solr_client.py` |
| Rebuild all search records | `usep_indexer_app/lib/reindex.py` |
| Website routes and search | `config/urls.py`; `usep_app/views.py`; `usep_app/search.py` |
| Website database and search helpers | `usep_app/models.py`: `FlatCollection`, general-page models, `Collection`, and `SolrHelper` |
| Detailed inscription display | `usep_app/usep_templates/display_inscription.html`; `usep-data/resources/xsl/USEp_display.xsl` |
| Instructions used to build search records | `usep-data/resources/xsl/USEp_to_Solr.xsl` and `transcription_index_val.xsl`, selected through indexer settings |

The indexer’s Python helpers are under `usep_indexer_app/lib/`. The older website keeps substantial search and display logic in `usep_app/models.py` as well as its views and templates.

Configuration connects each application to its data and services. Both use settings outside the repository-code. 
- The indexer’s key setting names include `USEP_DATA_GIT_CLONED_DIR_PATH`, `WEBSERVED_DATA_DIR_PATH`, `SPOOL_ROOT_PATH`, `SOLR_URL`, `SOLR_XSL_PATH`, and `TRANSCRIPTION_PARSER_XSL_PATH`. 
- The website’s settings select the Solr query URL and the public XML/XSL URLs. 


## Update timing and failures

- **A successful webhook response means the notice was saved.** It does not mean the site has finished updating.
- **Timing depends on cron and the work to do.** Add the wait for the next cron run, processing time, and Solr’s time to make changes available. Currently cron checks to see if there are updates that need to be processed every-two-minutes.
- **The USEP webapp's links to server-XML and Solr are updated separately.** Files are copied before indexing. A page’s XML can therefore be newer than its search record while indexing is underway or after a failure.
- **Some work can succeed before another part fails.** Valid records in a batch can be updated, while invalid records fail. 
- **Errors are reported according to configuration.** Recognized data problems are grouped into an editor email; technical failures alert administrators. 

---
