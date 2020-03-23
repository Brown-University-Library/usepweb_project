# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime, json, logging, os, pprint
from . import models, settings_app
from .models import AboutPage, ContactsPage, LinksPage, PublicationsPage, TextsPage  # static pages
from .models import DisplayInscriptionHelper, FlatCollection
from django.conf import settings as project_settings
from django.contrib.auth import logout
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.shortcuts import get_object_or_404, render
from usep_app.libs.version_helper import Versioner


log = logging.getLogger(__name__)
versioner = Versioner()


def info( request ):
    """ Displays branch and commit for easy comparison between localdev, dev, and production web-apps. """
    rq_now = datetime.datetime.now()
    commit = versioner.get_commit()
    branch = versioner.get_branch()
    info_txt = commit.replace( 'commit', branch )
    resp_now = datetime.datetime.now()
    taken = resp_now - rq_now
    context_dct = versioner.make_context( request, rq_now, info_txt, taken )
    output = json.dumps( context_dct, sort_keys=True, indent=2 )
    return HttpResponse( output, content_type='application/json; charset=utf-8' )


def error_check( request ):
    """ For checking that admins receive error-emails. """
    if project_settings.DEBUG == True:
        1/0
    else:
        return HttpResponseNotFound( '<div>404 / Not Found</div>' )


def collections( request ):
  """Displays list of collections by Region."""
  log.debug( 'starting collections()' )
  start_time = datetime.datetime.now()
  ## helpers ##
  def prepare_data():
    fc = FlatCollection()
    all_collections_objects = FlatCollection.objects.all().order_by( 'region_name', 'collection_code' )
    all_collections_dictionaries = [ obj.as_dict() for obj in all_collections_objects ]
    data_dict = {
      'region_codes': fc.make_region_codes_list(),
      'all_collections_dictionaries': all_collections_dictionaries,
      # 'login_url': reverse('admin:usep_app_flatcollection_changelist' ),
      'admin_links_url': reverse( 'admn_links_url' ),
      'search_url': reverse( 'search_url' ), 'collections_url': reverse( 'search_url' ), 'publications_url': reverse( 'publications_url' ),
      'texts_url': reverse( 'texts_url' ), 'links_url': reverse( 'links_url' ), 'about_url': reverse( 'about_url' ), 'contact_url': reverse( 'contact_url' ),
    }
    log.debug( 'data_dict (partial), ```%s```...' % pprint.pformat(data_dict)[0:1000] )
    return data_dict
  def build_response( format, callback ):
    if format == 'json':
      output = json.dumps( data_dict, sort_keys=True, indent=2 )
      if callback:
        output = '%s(%s)' % ( callback, output )
      return HttpResponse( output, content_type = 'application/javascript; charset=utf-8' )
    else:
      return render( request, 'usep_templates/collectionS.html', data_dict )
  ## work ##
  data_dict = prepare_data()
  format = request.GET.get( 'format', None )
  callback = request.GET.get( 'callback', None )
  response = build_response( format, callback )
  elapsed_time = unicode( datetime.datetime.now() - start_time )
  log.debug( 'elapsed time, ```%s```' % elapsed_time )
  return response


def collection( request, collection ):
    """Displays list of inscriptions for given collection."""
    ## helpers ##
    def prepare_data():
        c = models.Collection()
        solr_data = c.get_solr_data( collection )
        inscription_dict, num, display_dict = c.enhance_solr_data( solr_data, request.META[u'wsgi.url_scheme'], request.get_host() )
        data_dict = {
            u'collection_title': collection,
            u'inscriptions': inscription_dict,
            u'inscription_count': num,
            u'display': display_dict,
            u'flat_collection': FlatCollection.objects.get(collection_code=collection),
            u'show_dates':False,
            }
        return data_dict
    def build_response( format, callback ):
        if format == u'json':
            output = json.dumps( data_dict, sort_keys=True, indent=2 )
            if callback:
                output = u'%s(%s)' % ( callback, output )
            return HttpResponse( output, content_type = u'application/javascript; charset=utf-8' )
        else:
            return render( request, u'usep_templates/collectioN.html', data_dict )
    ## work ##
    log.debug( 'starting collection()' )
    start_time = datetime.datetime.now()
    data_dict = prepare_data()
    # log.debug( 'data_dict (partial), ```{}```...'.format(pprint.pformat(data_dict))[0:1000] )
    log.debug( 'data_dict (partial), ```%s```...' % pprint.pformat(data_dict)[0:1000] )
    format = request.GET.get( u'format', None )
    callback = request.GET.get( u'callback', None )
    response = build_response( format, callback )
    elapsed_time = unicode( datetime.datetime.now() - start_time )
    log.debug( 'elapsed time, ```%s```' % elapsed_time )
    return response


# def display_inscription( request, inscription_id ):
#     """ Displays inscription html from saxon-ce rendering of source xml and an include file of bib data,
#       which is then run through an xsl transform. """
#     log.debug( u'display_inscription() starting' )
#     start_time = datetime.datetime.now()
#     display_inscription_helper = DisplayInscriptionHelper()  # models.py
#     source_xml_url = display_inscription_helper.build_source_xml_url(
#         settings_app.DISPLAY_INSCRIPTION_XML_URL_PATTERN, request.is_secure(), request.get_host(), inscription_id )
#     context = display_inscription_helper.build_context(
#         request.get_host(),
#         project_settings.STATIC_URL,
#         inscription_id,
#         source_xml_url,
#         settings_app.DISPLAY_INSCRIPTION_XSL_URL,
#         settings_app.DISPLAY_INSCRIPTION_SAXONCE_FILE_URL,
#         settings_app.DISPLAY_INSCRIPTION_XIPR_URL )
#     # log.debug( u'display_inscription() context, %s' % pprint.pformat(context) )
#     log.debug( u'display_inscription() context (partial), ```%s```...' % pprint.pformat(context)[0:1000] )
#     elapsed_time = unicode( datetime.datetime.now() - start_time )
#     log.debug( 'elapsed time, ```%s```' % elapsed_time )
#     return render( request, u'usep_templates/display_inscription.html', context )


def display_inscription( request, inscription_id ):
    """ Displays inscription html from saxon-ce rendering of source xml and an include file of bib data,
      which is then run through an xsl transform. """
    log.debug( u'display_inscription() starting' )
    start_time = datetime.datetime.now()
    display_inscription_helper = DisplayInscriptionHelper()  # models.py
    source_xml_url = display_inscription_helper.build_source_xml_url(
        settings_app.DISPLAY_INSCRIPTION_XML_URL_PATTERN, request.is_secure(), request.get_host(), inscription_id )
    context = display_inscription_helper.build_context(
        request.get_host(),
        project_settings.STATIC_URL,
        inscription_id,
        source_xml_url,
        settings_app.DISPLAY_INSCRIPTION_XSL_URL,
        settings_app.DISPLAY_INSCRIPTION_SAXONCE_FILE_URL,
        settings_app.DISPLAY_INSCRIPTION_XIPR_URL )
    # log.debug( u'display_inscription() context, %s' % pprint.pformat(context) )
    log.debug( u'display_inscription() context (partial), ```%s```...' % pprint.pformat(context)[0:1000] )
    elapsed_time = unicode( datetime.datetime.now() - start_time )
    log.debug( 'elapsed time, ```%s```' % elapsed_time )

    if request.GET.get('format', '') == 'json':
        resp = HttpResponse( json.dumps(context, sort_keys=True, indent=2), content_type='application/javascript; charset=utf-8' )
    else:
        resp = render( request, u'usep_templates/display_inscription.html', context )
    log.debug( 'returning resp' )
    return resp


def publications( request ):
    """ Displays list of Corpora, Journals, Monographs, and Unpublished/Missing citations. """
    log.debug( 'publications() starting' )
    start_time = datetime.datetime.now()
    hostname = request.get_host()
    custom_static_url = project_settings.STATIC_URL
    publications_stylesheet_url = settings_app.DISPLAY_PUBLICATIONS_XSL_URL
    publications_xml_url = settings_app.DISPLAY_PUBLICATIONS_BIB_URL
    if hostname.lower() == u"usepigraphy.brown.edu":
        custom_static_url = custom_static_url.replace(u"library.brown.edu", u"usepigraphy.brown.edu")
        publications_stylesheet_url = publications_stylesheet_url.replace(u"library.brown.edu", u"usepigraphy.brown.edu")
        publications_xml_url = publications_xml_url.replace(u"library.brown.edu", u"usepigraphy.brown.edu")
    data_dict = {
        u'publications_stylesheet_url': publications_stylesheet_url,
        u'publications_xml_url': publications_xml_url,
        u'custom_static_url': custom_static_url,
    }
    elapsed_time = unicode( datetime.datetime.now() - start_time )
    log.debug( 'elapsed time, ```%s```' % elapsed_time )
    return render( request, u'usep_templates/publications.html', data_dict )


def pub_children( request, publication ):
    """displays listing of inscriptions for publication"""
    log.debug( 'pub_children() starting' )
    start_time = datetime.datetime.now()

    log.debug( u'publication: %s' % publication )
    assert type( publication ) == unicode

    publications_xml_url = settings_app.DISPLAY_PUBLICATIONS_BIB_URL
    elements = []
    try:
        r = requests.get(publications_xml_url)
        xml = etree.fromstring(r.content)
        elements = etree.XPath("//t:bibl[@xml:id='{0}']/t:title".format(publication), namespaces={"t":"http://www.tei-c.org/ns/1.0"})(xml)
    except Exception, e:
        log.error("Exception retrieving titles.xml: ", repr(e))

    title = elements[0].text if elements else publication

    #print "calling the Publication model"
    pub = models.Publication()
    pub.getPubData( publication )
    pub.buildInscriptionList( request.META[u'wsgi.url_scheme'], request.get_host() )
    pub.makeImageUrls()
    data_dict = {
        u'publication_title': title,
        u'inscriptions': pub.inscription_entries,
        u'inscription_count': pub.inscription_count, }
    ## respond
    format = request.GET.get( u'format', None )
    callback = request.GET.get( u'callback', None )

    elapsed_time = unicode( datetime.datetime.now() - start_time )
    log.debug( 'elapsed time, ```%s```' % elapsed_time )

    if format == u'json':
        output = json.dumps( data_dict, sort_keys=True, indent=2 )
        if callback:
            output = u'%s(%s)' % ( callback, output )
        return HttpResponse( output, content_type = u'application/javascript; charset=utf-8' )
    else:
        return render( request, u'usep_templates/publicatioN.html', data_dict )


def admin_links( request ):
    """ Displays admin-links. """
    context = {
        'collections_admin_url': reverse( 'admin:usep_app_flatcollection_changelist' ),
        'reindex_all_url': settings_app.REINDEX_ALL_URL,
        'delete_orphans_url': settings_app.DELETE_ORPHANS_URL
        }
    format = request.GET.get( 'format', None )
    if format == 'json':
        output = json.dumps( context, sort_keys=True, indent=2 )
        return HttpResponse( output, content_type='application/json; charset=utf-8' )
    else:
        return render( request, 'usep_templates/admin_links.html', context )
    # return HttpResponse( 'admin-links page coming' )


def delete_orphans( request ):
    """ Manages solr orphan deletion. """
    return HttpResponse( 'solr-orphan-deletion coming' )


## static pages  ##


def texts( request ):
    page_data = TextsPage.objects.all()
    page_data = page_data[0] if page_data else []  # just one record
    page_dct = {
        'page_data': page_data,
        'settings_app': settings_app }
    return render( request, u'usep_templates/static.html', page_dct )

def links( request ):
  page_data = LinksPage.objects.all()[0]  # just one record
  page_dct = {
    u'page_data': page_data,
    u'settings_app': settings_app }
  return render( request, u'usep_templates/static.html', page_dct )
  # return render_to_response( u'usep_templates/static.html', page_dct )

def about( request ):
  page_data = AboutPage.objects.all()[0]  # just one record
  page_dct = {
    u'page_data': page_data,
    u'settings_app': settings_app }
  return render( request, u'usep_templates/static.html', page_dct )
  # return render_to_response( u'usep_templates/static.html', page_dct )

def contact( request ):
  page_data = ContactsPage.objects.all()[0]  # just one record
  page_dct = {
    u'page_data': page_data,
    u'settings_app': settings_app }
  return render( request, u'usep_templates/static.html', page_dct )
  # return render_to_response( u'usep_templates/static.html', page_dct )
