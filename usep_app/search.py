# -*- coding: utf-8 -*-

## TODO: merge into views.py



import datetime
import logging

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from requests.exceptions import HTTPError

from usep_app import models


log = logging.getLogger(__name__)


def search_form(request):
    log.debug( 'search.search_form() starting' )
    start_time = datetime.datetime.now()

    sh = models.SolrHelper()

    results, facets, querystring = sh.query({"*":"*"}, {"rows":0}, search_form=True)

    field_list = ["text_genre", "object_type", "material", "language", "writing", "condition", "char"]
    f = []
    for x in field_list:
        f += [(x, facets[x])]

    elapsed_time = str( datetime.datetime.now() - start_time )
    log.debug( 'elapsed time, ```%s```' % elapsed_time )

    return render(request, 'usep_templates/search_form.html', {"facets":f})


def results(request: HttpRequest) -> HttpResponse:
    log.debug( 'search.results() starting' )
    start_time = datetime.datetime.now()

    q = dict(request.GET)

    sh = models.SolrHelper()

    try:
        results, facets, querystring = sh.query(q, {'rows': 4000})
    except HTTPError as exc:
        if exc.response is None or exc.response.status_code != 400:
            raise
        return render(request, 'usep_templates/results.html', {'invalid_search': True}, status=400)

    show_dates = "notAfter" in querystring

    data_dict = {"q":q, "title":"Search", "facets":facets, "url":request.get_full_path(), "querystring":querystring, "show_dates":show_dates}
    data_dict['results'] = sh.enhance_solr_data(results, request.META['wsgi.url_scheme'], request.get_host())

    elapsed_time = str( datetime.datetime.now() - start_time )
    log.debug( 'elapsed time, ```%s```' % elapsed_time )

    return render(request, 'usep_templates/results.html', data_dict)
