## TODO: merge into views.py


import logging
from time import monotonic

from django.core.exceptions import TooManyFieldsSent, ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from requests.exceptions import HTTPError

from usep_app import models
from usep_app.libs.search_query import FORM_FILTERS, MAX_QUERY_BYTES

log = logging.getLogger(__name__)


def search_form(request: HttpRequest) -> HttpResponse:
    """
    Displays the search form with choices from the catalog.
    Called by: Django's URL dispatcher.
    """
    log.debug('search.search_form() starting')
    start_time = monotonic()

    sh = models.SolrHelper()

    _, facets, _ = sh.query({}, {'rows': 0}, search_form=True)
    form_facets = [(field, facets[field]) for field in FORM_FILTERS]

    elapsed_time = monotonic() - start_time
    log.debug('elapsed_time_seconds, ``%.3f``', elapsed_time)

    return render(request, 'usep_templates/search_form.html', {'facets': form_facets})


def results(request: HttpRequest) -> HttpResponse:
    """
    Checks the search controls and displays matching inscriptions or an input error.
    Called by: Django's URL dispatcher.
    """
    log.debug('search.results() starting')
    start_time = monotonic()

    sh = models.SolrHelper()
    try:
        if len(request.META.get('QUERY_STRING', '')) > MAX_QUERY_BYTES:
            raise ValidationError('Please shorten the search or choose fewer filters.')
        q = dict(request.GET.lists())
        results, facets, querystring = sh.query(q, {'rows': 4000})
    except (ValidationError, TooManyFieldsSent) as exc:
        message = exc.messages[0] if isinstance(exc, ValidationError) else 'Please choose fewer filters.'
        return render(request, 'usep_templates/results.html', {'invalid_search': True, 'search_error': message}, status=400)
    except HTTPError as exc:
        if exc.response is None or exc.response.status_code not in (400, 414):
            raise
        return render(request, 'usep_templates/results.html', {'invalid_search': True}, status=400)

    show_dates = bool(request.GET.get('notBefore', '').strip() and request.GET.get('notAfter', '').strip())
    filter_url = request.get_full_path() + ('&' if request.META.get('QUERY_STRING') else '?')

    data_dict = {
        'q': q,
        'title': 'Search',
        'facets': facets,
        'filter_url': filter_url,
        'querystring': querystring,
        'show_dates': show_dates,
    }
    data_dict['results'] = sh.enhance_solr_data(results, request.META['wsgi.url_scheme'], request.get_host())

    elapsed_time = monotonic() - start_time
    log.debug('elapsed_time_seconds, ``%.3f``', elapsed_time)

    return render(request, 'usep_templates/results.html', data_dict)
