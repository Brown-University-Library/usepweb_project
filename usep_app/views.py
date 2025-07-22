# -*- coding: utf-8 -*-



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
  log.debug( '\n\nstarting collections()' )
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
  elapsed_time = str( datetime.datetime.now() - start_time )
  log.debug( 'elapsed time, ```%s```' % elapsed_time )
  return response


# def collection( request, collection ):
#     """Displays list of inscriptions for given collection."""
#     ## helpers ##
#     def prepare_data():
#         log.debug( 'starting collection->prepare_data()' )
#         c = models.Collection()
#         solr_data = c.get_solr_data( collection )
#         if solr_data == []:
#             data_dict = {}
#         else:
#             inscription_dict, num, display_dict = c.enhance_solr_data( solr_data, request.META[u'wsgi.url_scheme'], request.get_host() )
#             data_dict = {
#                 u'collection_title': collection,
#                 u'inscriptions': inscription_dict,
#                 u'inscription_count': num,
#                 u'display': display_dict,
#                 u'flat_collection': FlatCollection.objects.get(collection_code=collection),
#                 u'show_dates':False,
#                 }
#         return data_dict
#     def build_response( format, callback ):
#         if format == u'json':
#             output = json.dumps( data_dict, sort_keys=True, indent=2 )
#             if callback:
#                 output = u'%s(%s)' % ( callback, output )
#             return HttpResponse( output, content_type = u'application/javascript; charset=utf-8' )
#         else:
#             return render( request, u'usep_templates/collectioN.html', data_dict )
#     ## work ##
#     log.debug( 'starting collection()' )
#     start_time = datetime.datetime.now()
#     data_dict = prepare_data()
#     if data_dict == {}:
#         return HttpResponseNotFound( '404 / Not Found' )
#     # log.debug( 'data_dict (partial), ```{}```...'.format(pprint.pformat(data_dict))[0:1000] )
#     log.debug( 'data_dict (partial), ```%s```...' % pprint.pformat(data_dict)[0:1000] )
#     format = request.GET.get( u'format', None )
#     callback = request.GET.get( u'callback', None )
#     response = build_response( format, callback )
#     elapsed_time = unicode( datetime.datetime.now() - start_time )
#     log.debug( 'elapsed time, ```%s```' % elapsed_time )
#     return response


def collection( request, collection ):
    """Displays list of inscriptions for given collection."""
    log.debug( '\n\nstarting collection(); collection, ``%s``' % collection )
    ## helpers ##
    def prepare_data():
        log.debug( 'starting collection->prepare_data()' )
        c = models.Collection()
        solr_data = c.get_solr_data( collection )  ## list
        log.debug('Returned to collection view')
        log.debug( 'type(solr_data), ``%s``' % type(solr_data) )
        data_dict = 'init'
        if solr_data == []:
            log.debug( 'solr_data empty; setting data_dict to {}' )
            data_dict = {}
        if data_dict == 'init':
            try:
                flat_collection = FlatCollection.objects.get( collection_code=collection )
            except:
                log.exception( 'no collection found; traceback follows; processing will continue; setting data_dict to {}' )
                data_dict = {}
        if data_dict == 'init':
            log.debug( 'data_dict looks good' )
            inscription_dict, num, display_dict = c.enhance_solr_data( solr_data, request.META['wsgi.url_scheme'], request.get_host() )
            for key, val in display_dict.items():
                log.debug('DISPLAY DICT: {0}'.format(key))
            for key, val in inscription_dict.items():
                log.debug('INSCRIPTION DICT: {0}'.format(key))
            # log.debug( 'inscription_dict, ``%s``' % pprint.pformat(inscription_dict) )
            # log.debug( 'display_dict, ``%s``' % pprint.pformat(display_dict) )
            log.debug( 'type(inscription_dict), ``%s``' % type(inscription_dict) )
            log.debug( 'type(display_dict), ``%s``' % type(display_dict) )
            data_dict = {
                'collection_title': collection,
                'inscriptions': inscription_dict,
                'inscription_count': num,
                'display': display_dict,
                'flat_collection': FlatCollection.objects.get(collection_code=collection),
                'show_dates':False,
                }
        return data_dict
    def build_response( format, callback ):
        if format == 'json':
            output = json.dumps( data_dict, sort_keys=True, indent=2 )
            if callback:
                output = '%s(%s)' % ( callback, output )
            return HttpResponse( output, content_type = 'application/javascript; charset=utf-8' )
        else:
            return render( request, 'usep_templates/collectioN.html', data_dict )
    ## work ##
    start_time = datetime.datetime.now()
    data_dict = prepare_data()
    log.debug( 'type(data_dict), ``%s``' % type(data_dict) )
    if data_dict == {}:
        return HttpResponseNotFound( '404 / Not Found' )
    # log.debug( 'data_dict (partial), ```{}```...'.format(pprint.pformat(data_dict))[0:1000] )
    log.debug( 'data_dict (partial), ```%s```...' % pprint.pformat(data_dict)[0:1000] )
    format = request.GET.get( 'format', None )
    callback = request.GET.get( 'callback', None )
    response = build_response( format, callback )
    elapsed_time = str( datetime.datetime.now() - start_time )
    log.debug( 'elapsed time, ```%s```' % elapsed_time )
    return response


def display_inscription( request, inscription_id ):
    """ Displays inscription html from saxon-ce rendering of source xml and an include file of bib data,
      which is then run through an xsl transform. """
    log.debug( 'display_inscription() starting' )
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
    log.debug( 'display_inscription() context (partial), ```%s```...' % pprint.pformat(context)[0:1000] )
    elapsed_time = str( datetime.datetime.now() - start_time )
    log.debug( 'elapsed time, ```%s```' % elapsed_time )

    if request.GET.get('format', '') == 'json':
        resp = HttpResponse( json.dumps(context, sort_keys=True, indent=2), content_type='application/javascript; charset=utf-8' )
    else:
        resp = render( request, 'usep_templates/display_inscription.html', context )
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
    if hostname.lower() == "usepigraphy.brown.edu":
        custom_static_url = custom_static_url.replace("library.brown.edu", "usepigraphy.brown.edu")
        publications_stylesheet_url = publications_stylesheet_url.replace("library.brown.edu", "usepigraphy.brown.edu")
        publications_xml_url = publications_xml_url.replace("library.brown.edu", "usepigraphy.brown.edu")
    data_dict = {
        'publications_stylesheet_url': publications_stylesheet_url,
        'publications_xml_url': publications_xml_url,
        'custom_static_url': custom_static_url,
    }
    elapsed_time = str( datetime.datetime.now() - start_time )
    log.debug( 'elapsed time, ```%s```' % elapsed_time )
    return render( request, 'usep_templates/publications.html', data_dict )


def pub_children( request, publication ):
    """displays listing of inscriptions for publication"""
    log.debug( 'pub_children() starting' )
    start_time = datetime.datetime.now()

    log.debug( 'publication: %s' % publication )
    assert type( publication ) == str

    publications_xml_url = settings_app.DISPLAY_PUBLICATIONS_BIB_URL
    elements = []
    try:
        r = requests.get(publications_xml_url)
        xml = etree.fromstring(r.content)
        elements = etree.XPath("//t:bibl[@xml:id='{0}']/t:title".format(publication), namespaces={"t":"http://www.tei-c.org/ns/1.0"})(xml)
    except Exception as e:
        log.error("Exception retrieving titles.xml: ", repr(e))

    title = elements[0].text if elements else publication

    #print "calling the Publication model"
    pub = models.Publication()
    pub.getPubData( publication )
    pub.buildInscriptionList( request.META['wsgi.url_scheme'], request.get_host() )
    pub.makeImageUrls()
    data_dict = {
        'publication_title': title,
        'inscriptions': pub.inscription_entries,
        'inscription_count': pub.inscription_count, }
    ## respond
    format = request.GET.get( 'format', None )
    callback = request.GET.get( 'callback', None )

    elapsed_time = str( datetime.datetime.now() - start_time )
    log.debug( 'elapsed time, ```%s```' % elapsed_time )

    if format == 'json':
        output = json.dumps( data_dict, sort_keys=True, indent=2 )
        if callback:
            output = '%s(%s)' % ( callback, output )
        return HttpResponse( output, content_type = 'application/javascript; charset=utf-8' )
    else:
        return render( request, 'usep_templates/publicatioN.html', data_dict )


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
    return render( request, 'usep_templates/static.html', page_dct )

def links( request ):
  page_data = LinksPage.objects.all()[0]  # just one record
  page_dct = {
    'page_data': page_data,
    'settings_app': settings_app }
  return render( request, 'usep_templates/static.html', page_dct )
  # return render_to_response( u'usep_templates/static.html', page_dct )

def about( request ):
  page_data = AboutPage.objects.all()[0]  # just one record
  page_dct = {
    'page_data': page_data,
    'settings_app': settings_app }
  return render( request, 'usep_templates/static.html', page_dct )
  # return render_to_response( u'usep_templates/static.html', page_dct )

def contact( request ):
  page_data = ContactsPage.objects.all()[0]  # just one record
  page_dct = {
    'page_data': page_data,
    'settings_app': settings_app }
  return render( request, 'usep_templates/static.html', page_dct )
  # return render_to_response( u'usep_templates/static.html', page_dct )
