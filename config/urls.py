# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.conf.urls import url
from django.contrib import admin
from django.views.generic import RedirectView
from usep_app import search, views


admin.autodiscover()


urlpatterns = [

    ## primary app urls...

    url( r'^usep/collections/$',  views.collections, name='collections_url' ),
    url( r'^usep/collections/(?P<collection>[^/]+)/$',  views.collection, name='collection_url' ),
    url( r'^usep/inscription/(?P<inscription_id>[^/]+)/$', views.display_inscription, name='inscription_url' ),

    url( r'^usep/publications/$',  views.publications, name='publications_url' ),
    url( r'^usep/publication/(?P<publication>[^/]+)/$', views.pub_children, name='publication_url' ),

    url( r'^usep/texts/$',  views.texts, name='texts_url' ),
    url( r'^usep/links/$',  views.links, name='links_url' ),
    url( r'^usep/about/$',  views.about, name='about_url' ),
    url( r'^usep/contact/$',  views.contact, name='contact_url' ),

    url( r'^usep/search/$', search.search_form, name='search_url'),
    url( r'^usep/search/results/$', search.results, name='search_results_url'),

    url( r'^usep/$',  RedirectView.as_view(pattern_name='collections_url') ),

    ## support urls...

    url( r'^usep/info/$',  views.info, name='info_url' ),  ## TODO- retire after 2021-May-01
    url( r'^usep/version/$',  views.info, name='info_url' ),
    url( r'^usep/error_check/$', views.error_check, name='error_check_url' ),  # only generates error if DEBUG == True

    ## other...

    url( r'^usep/admin/links/$',  views.admin_links, name='admn_links_url' ),
    url( r'^usep/admin/', admin.site.urls),

    ]
