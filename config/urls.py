# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.conf.urls import include, re_path
from django.contrib import admin
from django.views.generic import RedirectView
from usep_app import search, views


admin.autodiscover()


urlpatterns = [

    ## primary app urls...

    re_path( r'^usep/collections/$',  views.collections, name='collections_url' ),
    re_path( r'^usep/collections/(?P<collection>[^/]+)/$',  views.collection, name='collection_url' ),
    re_path( r'^usep/inscription/(?P<inscription_id>[^/]+)/$', views.display_inscription, name='inscription_url' ),

    re_path( r'^usep/publications/$',  views.publications, name='publications_url' ),
    re_path( r'^usep/publication/*$', views.pub_children, name='publication_url' ), # TODO should be more specific

    re_path( r'^usep/texts/$',  views.texts, name='texts_url' ),
    re_path( r'^usep/links/$',  views.links, name='links_url' ),
    re_path( r'^usep/about/$',  views.about, name='about_url' ),
    re_path( r'^usep/contact/$',  views.contact, name='contact_url' ),

    re_path( r'^usep/search/$', search.search_form, name='search_url'),
    re_path( r'^usep/search/results/*$', search.results, name='search_results_url'), # TODO should be more specific

    re_path( r'^usep/$',  RedirectView.as_view(pattern_name='collections_url') ),

    ## support urls...

    re_path( r'^usep/info/$',  views.info, name='info_url' ),  ## TODO- retire after 2021-May-01
    re_path( r'^usep/version/$',  views.info, name='info_url' ),
    re_path( r'^usep/error_check/$', views.error_check, name='error_check_url' ),  # only generates error if DEBUG == True

    ## other...

    re_path( r'^usep/admin/links/$',  views.admin_links, name='admn_links_url' ),
    re_path( r'^usep/admin/', admin.site.urls),

    ]
