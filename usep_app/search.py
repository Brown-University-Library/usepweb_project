# -*- coding: utf-8 -*-

## TODO: merge into views.py



import datetime, json, logging, pprint
import requests
from django.conf import settings as settings_project
from django.urls import reverse
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from usep_app import settings_app, models


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


def results(request):
    log.debug( 'search.results() starting' )
    start_time = datetime.datetime.now()

    q = dict(request.GET)

    sh = models.SolrHelper()

    results, facets, querystring = sh.query(q, {"rows": 4000})

    show_dates = "notAfter" in querystring

    data_dict = {"q":q, "title":"Search", "facets":facets, "url":request.get_full_path(), "querystring":querystring, "show_dates":show_dates}
    if 'error' in results:
        data_dict['error'] = results['error']
    else:
        data_dict['results'] = sh.enhance_solr_data(results, request.META['wsgi.url_scheme'], request.get_host())

    elapsed_time = str( datetime.datetime.now() - start_time )
    log.debug( 'elapsed time, ```%s```' % elapsed_time )

    return render(request, 'usep_templates/results.html', data_dict)
