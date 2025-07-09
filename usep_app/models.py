# -*- coding: utf-8 -*-



import collections, json, logging, os, pprint
from operator import itemgetter  # for a comparator sort

import requests
from django.conf import settings as settings_project
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import smart_str
from usep_app import settings_app

from django.utils.http import urlencode

from lxml import etree

import string

log = logging.getLogger(__name__)



### django-db collection class ###


class FlatCollection( models.Model ):
    """ Represents non-hierarchical collection. """
    collection_code = models.CharField( blank=True, max_length=50 )
    region_code = models.CharField( blank=True, max_length=10 )
    region_name = models.CharField( blank=True, max_length=50 )
    settlement_code = models.CharField( blank=True, max_length=10 )
    institution_code = models.CharField( blank=True, max_length=10 )
    repository_code = models.CharField( blank=True, max_length=10 )
    collection_name = models.CharField( blank=True, max_length=100 )
    collection_address = models.CharField( blank=True, max_length=200, help_text='single string' )
    collection_url = models.CharField( blank=True, max_length=200 )
    collection_description = models.TextField( blank=True )

    def __unicode__(self):
        return smart_str( self.collection_code, 'utf-8', 'replace' )

    def save(self):
        """ Auto-builds collection_code from component parts if they exist. """
        if len( self.collection_code.strip() ) == 0:
            new_collection_code = self.region_code.strip()
            if len( self.settlement_code.strip() ) > 0:
                new_collection_code = '%s.%s' % ( new_collection_code, self.settlement_code.strip() )
            if len( self.institution_code.strip() ) > 0:
                new_collection_code = '%s.%s' % ( new_collection_code, self.institution_code.strip() )
            if len( self.repository_code.strip() ) > 0:
                new_collection_code = '%s.%s' % ( new_collection_code, self.repository_code.strip() )
            self.collection_code = new_collection_code
        super(FlatCollection, self).save() # Call the "real" save() method

    def as_dict(self):
        """ Allows easy serializing to json of queryset. """
        return {
            'collection_code': self.collection_code,
            'region_code': self.region_code,
            'region_name': self.region_name,
            'settlement_code': self.settlement_code,
            'institution_code': self.institution_code,
            'repository_code': self.repository_code,
            'collection_name': self.collection_name,
            'collection_address': self.collection_address,
            'collection_url': self.collection_url,
            'collection_description': self.collection_description,
        }

    def make_region_codes_list(self):
        """ Returns unique sorted list of region codes. """
        from usep_app.models import FlatCollection
        q = FlatCollection.objects.values('region_code').distinct()  # type: <class 'django.db.models.query.ValuesQuerySet'>; eg: [{'region_code': u'CA'}, {'region_code': u'MA'}]
        region_codes = []
        for entry in q:
            list_entry = list(entry.values())
            value = list_entry[0]
            region_codes.append(value)
        return sorted( region_codes )

    # end class FlatCollection


### django-db models for static pages ###


class AboutPage(models.Model):
    title_page = models.CharField( blank=True, max_length=100 )
    title_content = models.CharField( blank=True, max_length=100 )
    content = models.TextField( blank=True, help_text='HTML allowed.' )
    def __unicode__(self):
        return smart_str( self.title_page, 'utf-8', 'replace' )
    class Meta:
        verbose_name_plural = 'About page fields'


class TextsPage(models.Model):
    title_page = models.CharField( blank=True, max_length=100 )
    title_content = models.CharField( blank=True, max_length=100 )
    content = models.TextField( blank=True, help_text='HTML allowed.' )
    def __unicode__(self):
        return smart_str( self.title_page, 'utf-8', 'replace' )
    class Meta:
        verbose_name_plural = 'Texts page fields'


class LinksPage(models.Model):
    title_page = models.CharField( blank=True, max_length=100 )
    title_content = models.CharField( blank=True, max_length=100 )
    content = models.TextField( blank=True, help_text='HTML allowed.' )
    def __unicode__(self):
        return smart_str( self.title_page, 'utf-8', 'replace' )
    class Meta:
        verbose_name_plural = 'Links page fields'


class ContactsPage(models.Model):
    title_page = models.CharField( blank=True, max_length=100 )
    title_content = models.CharField( blank=True, max_length=100 )
    content = models.TextField( blank=True, help_text='HTML allowed.' )
    def __unicode__(self):
        return smart_str( self.title_page, 'utf-8', 'replace' )
    class Meta:
        verbose_name_plural = 'Contacts page fields'


class PublicationsPage(models.Model):
    title_page = models.CharField( blank=True, max_length=100 )
    title_content = models.CharField( blank=True, max_length=100 )
    content = models.TextField( blank=True, help_text='HTML allowed.' )
    def __unicode__(self):
        return smart_str( self.title_page, 'utf-8', 'replace' )
    class Meta:
        verbose_name_plural = 'Publication page fields'


### other non-db classes ###

# Function to pass to sorted() to sort the list of documents by weird free-form ids
# essentially splits them into numeric and non-numeric keys and returns whatever
# set it was able to break up
def id_sort(doc):
    """ Called by models.Collection.get_solr_data() """
    # idno = doc[u'msid_idno']
    idno = doc.get('msid_idno', 'no-msid_idno-found')

    # IN THE FUTURE:
    # add to this string to add new characters to split tokens over (splits over "." by default)
    split_characters = "-,/"
    # add to this string to add new characters that should be removed (e.g. "#")
    remove_characters = "#"

    for c in split_characters:
        idno = idno.replace(c, ".")
    for c in remove_characters:
        idno = idno.replace(c, "")

    keylist = []
    for x in idno.split("."):
        try:
            keylist += [int(x)]
        except ValueError:

            tokens = break_token(x)
            keylist += tokens

    return tuple(keylist)

# Break a mixed numeric/text token into numeric/non-numeric parts. Helper for id_sort
def break_token(token):
    idx1 = 0
    idx2 = 0
    parts = []
    numeric = (token[0] in string.digits) # True if we start with a numeric token, false otherwise

    # Loop through string and add subtokens to parts as necessary
    for c in token:
        condition = token[idx2] in string.digits
        if not numeric:
            condition = not condition


        if condition:
            idx2 += 1
        else:
            parts += [int(token[idx1:idx2])] if numeric else [token[idx1:idx2]]
            idx1 = idx2
            idx2 += 1
            numeric = not numeric

    parts += [token[idx1:idx2]]
    return parts

def separate_into_languages(docs):

    # log.debug( 'docs, ``%s``' % pprint.pformat(docs) )

    ## Language value/display pairs as of January-2021

    ## ordering the dict: <https://stackoverflow.com/questions/15711755/converting-dict-to-ordereddict>

    # language_pairs = {
    #     u"grc": u"Greek",
    #     u"lat": u"Latin",
    #     u"la": u"Latin",
    #     u"la-Grek": u"Latin written in Greek",
    #     u"lat-Grek":u"Latin written in Greek",
    #     u"ett": u"Etruscan",
    #     u"xrr": u"Raetic",
    #     u"hbo": u"Hebrew",
    #     u"phn": u"Punic",
    #     u"arc": u"Aramaic",
    #     u"ecy": u"Eteocypriot",
    #     u"und": u"Undecided",
    #     u"zxx": u"Non-linguistic",
    #     u"unknown": u"Unknown"
    # }

    language_pairs_list = [
        ('grc', 'Greek'),
        ('grc-Latn', 'Greek written in Latin'),
        ('grc-Cprt', 'Greek written in Cypriot'),
        ('lat', 'Latin'),
        ('la', 'Latin'),
        ('la-Grek', 'Latin written in Greek'),
        ('lat-Grek','Latin written in Greek'),
        ('arc', 'Aramaic'),
        ('ecy', 'Eteocypriot'),
        ('ett', 'Etruscan'),
        ('hbo', 'Hebrew'),
        ('phn', 'Punic'),
        ('xrr', 'Raetic'),
        ('zxx', 'Non-linguistic'),
        ('und', 'Undecided'),
        ('unknown', 'Unknown')
    ]
    language_pairs = collections.OrderedDict( language_pairs_list )
    # log.debug( 'language_pairs, ``%s``' % pprint.pformat(language_pairs) )

    ## create result-dict -- TODO: since I need an ordered-dict, change this to create the list of tuples to avoid the re-work of the dict.

    result = {}
    for doc in docs:
        language = doc.get('language', '')
        language = language[0] if type(language) == list else language
        if language in result:
            result[language]['docs'] += [doc]
        else:
            result[language] = {'docs': [doc], 'display': language_pairs.get(language, language)}
    # log.debug( 'language separation result, ``%s``' % result )
    # log.debug( 'type(result), ``%s``' % type(result) )
    # log.debug( 'result.keys(), ``%s``' % result.keys() )

    ## convert result-dict to ordered-dict
    desired_order_keys = []
    for language_tuple in language_pairs_list:
        language_code = language_tuple[0]
        desired_order_keys.append( language_code )
    result_intermediate_tuples = [ (key, result.get(key, None)) for key in desired_order_keys ]
    # log.debug( 'result_intermediate_tuples, ``%s``' % pprint.pformat(result_intermediate_tuples) )
    new_result = collections.OrderedDict( result_intermediate_tuples )
    # log.debug( 'language separation new_result, ``%s``' % new_result )
    # log.debug( 'type(new_result), ``%s``' % type(new_result) )
    # log.debug( 'new_result.keys(), ``%s``' % new_result.keys() )

    ## Actual display pairs used for convenience
    display_pairs_intermediate_tuples = []
    for item in list(new_result.items()):
        ( language_code, data ) = ( item[0], item[1] )
        if data != None:
            display_text = data['display']
            display_pairs_intermediate_tuples.append( (language_code, display_text) )
    # log.debug( 'display_pairs_intermediate_tuples, ``%s``' % display_pairs_intermediate_tuples )
    display_pairs = collections.OrderedDict( display_pairs_intermediate_tuples )

    log.debug( 'returning three-element tuple of (dict, int, dict)' )
    return (new_result, len(docs), display_pairs)


class Collection(object):
    """ Handles code to display the inscriptions list for a given collection. """

    def get_solr_data( self, collection ):
        """ Queries solr for collection info.
            Called by views.collection() """
        log.debug( 'starting Collection.get_solr_data()' )
        payload = {
            'q': "id:{0}*".format(collection),
            'fl': '*',
            'start': '0',
            'rows': '99000',
            'wt': 'json',
            'indent': 'on', }
        r = requests.get( settings_app.SOLR_URL_BASE, params=payload )
        log.debug( 'solr url, ```%s```' % r.url )
        d = json.loads( r.content.decode('utf-8', 'replace') )
        sorted_doc_list = sorted( d['response']['docs'], key=id_sort )  # sorts the doc-list on dict key 'msid_idno'
        log.debug( 'sorted_doc_list (first two), ```{}```...'.format(pprint.pformat(sorted_doc_list[0:2])) )
        return sorted_doc_list

    def enhance_solr_data( self, solr_data, url_scheme, server_name ):
        """ Adds to dict entries from solr: image-url and item-url.
            Called by views.collection() """
        log.debug( 'starting Collection.enhance_solr_data()' )
        enhanced_list = []
        for entry in solr_data:
            image_url = None
            if 'graphic_name' in list(entry.keys()):
                log.debug("enhance_solr_data graphic_name", entry['graphic_name'], entry['graphic_name'].startswith('http'))
                if entry['graphic_name'].startswith('https:') or entry['graphic_name'].startswith('http:'):
                    image_url = entry['graphic_name']
                else:
                    image_url = '%s/%s' % ( settings_app.INSCRIPTIONS_URL_SEGMENT, entry['graphic_name'] )
            entry['image_url'] = image_url
            entry['url'] = '%s://%s%s' % ( url_scheme, server_name, reverse('inscription_url', args=(entry['id'],)) )
            enhanced_list.append( entry )
        separated = separate_into_languages( enhanced_list )
        log.debug( 'type(separated), ``%s``' % type(separated) )
        return separated

    # end class Collection()


class DisplayInscriptionHelper( object ):
    """ Helper for views.display_inscription() """

    def build_source_xml_url( self, url_pattern, is_secure, hostname, inscription_id ):
        """ Returns url to inscription xml.
            Called by views.display_inscription() """
        scheme = 'https' if ( is_secure == True ) else 'http'
        url = url_pattern.replace( 'SCHEME', scheme )
        url = url.replace( 'HOSTNAME', hostname )
        url = url.replace( 'INSCRIPTION_ID', inscription_id )
        return url

    def build_context( self, hostname, custom_static_url, inscription_id, source_xml_url, xsl_url, saxonce_url, xipr_url ):
        """ Returns context dict.
            Called by views.display_inscription() """
        context = {
          'custom_static_url': self.update_host( hostname, custom_static_url ),
          'inscription_id': inscription_id,
          'source_xml_url': self.update_host( hostname, source_xml_url ),
          'xsl_url': self.update_host( hostname, xsl_url ),
          'saxonce_file_url': self.update_host( hostname, saxonce_url ),
          'xipr_url': self.update_host( hostname, xipr_url )
          }
        return context

    def update_host( self, hostname, url ):
        """ Updates url if needed.
            Called by build_context()
            Allows saxonce and ajax references to work with both `library.brown.edu` and `usepigraphy.brown.edu` urls.
            Note, eventually the https replacement may have to be removed. """
        if hostname.lower() == 'usepigraphy.brown.edu':
            url = url.replace( 'library.brown.edu', 'usepigraphy.brown.edu' )
            # url = url.replace( 'https', 'http' )
        return url

    # def update_host( self, hostname, url ):
    #     """ Updates url if needed.
    #         Allows saxonce and ajax references to work with both `library.brown.edu` and `usepigraphy.brown.edu` urls. """
    #     if hostname.lower() == u'usepigraphy.brown.edu':
    #         url = url.replace( 'library.brown.edu', 'usepigraphy.brown.edu' )
    #     return url

    # end class DisplayInscriptionHelper()


class Publication(object):

    def __init__(self):
        self.title = ''
        self.inscription_count = 0
        self.inscription_entries = []
        self.inscription_images = []  # used for thumbnails
        self.pub_solr_urls = []
        self.pub_solr_responses = []

    def getPubData( self, pub_id ):
        """
        Retrieves inscriptions with the given bib_id.
        """

        log.debug( 'len(self.inscription_entries) START: %s' % len(self.inscription_entries) )

        sh = SolrHelper()

        payload = dict( list(sh.default_params.items()) + list({
                'q':'bib_ids:{0}'.format(pub_id),
                'rows':'99999',
                'fl': '*',
                'sort': 'id asc'}.items())
                )
        r = requests.post( settings_app.SOLR_URL_BASE, payload )
        solr_response = r.content.decode('utf-8', 'replace')
        self.pub_solr_urls.append( r.url )
        self.pub_solr_responses.append( solr_response )
        json_resp = json.loads(solr_response)

        self.inscription_entries = json_resp['response']['docs']
        self.inscription_count = json_resp['response']['numFound']

        log.debug( 'self.inscription_entries END: %s' % self.inscription_entries[0:10] )
        return

    def buildInscriptionList( self, url_scheme, server_name ):
        """Adds item-url to inscription-dict list."""
        for item in self.inscription_entries:
            item['url'] = '%s://%s%s' % ( url_scheme, server_name, reverse('inscription_url', args=(item['id'],)) )
        return

    def makeImageUrls( self ):
        """Adds image_url to inscription-dict list."""
        for item in self.inscription_entries:
            image_url = None
            if 'graphic_name' in list(item.keys()):
                log.debug("makeImageUrls graphic_name", item['graphic_name'], item['graphic_name'].startswith('http:'))
                if item['graphic_name'].startswith('https:') or item['graphic_name'].startswith('http:'):
                    image_url = item['graphic_name']
                else:
                    image_url = '%s/%s' % ( settings_app.INSCRIPTIONS_URL_SEGMENT, item['graphic_name'] )
            item['image_url'] = image_url
        return

    # end class Publication()


class Publications(object):

    def __init__(self):
        self.corpora = []  # list for display
        self.corpora_dict = {}  # dict of key=title & value=inscription_id list
        self.journals = []
        self.journals_dict = {}
        self.monographs = []
        self.monographs_dict = {}
        # self.monographs_citation = {} # dict of key=title & value=citation in format <author>, <title>. [<bib_id>]
        self.master_pub_dict = {}
        self.pubs_solr_url = None
        self.pubs_solr_response = None
        self.pubs_entries = None

    def getPubData(self):
        """Gets solr publication data for self.buildPubLists()"""
        #print "models.py: Publications: getPubData"

        sh = SolrHelper()
        payload = dict( list(sh.default_params.items()) + list({
            'q': 'bib_ids_types:*',
            'rows': '99999',
            'fl': 'id, bib_ids, bib_ids_types, bib_titles, bib_titles_all, bib_authors, status' }.items())
            )

        #print "\tAbout to make request!"
        r = requests.get( settings_app.SOLR_URL_BASE, params=payload )

        #print "\tReturned from the get request"
        log.debug( 'publications solr call: %s' % r.url )
        self.pubs_solr_url = r.url
        self.pubs_solr_response = r.content.decode( 'utf-8', 'replace' )
        jdict = json.loads( self.pubs_solr_response )
        log.debug( 'publications solr query result dict keys.response: %s' % list(jdict.keys()) )
        log.debug( 'publications solr query result dict["response"] keys: %s' % list(jdict['response'].keys()) )
        log.debug( 'publications solr query result dict["response"]["numFound"]: %s' % jdict['response']['numFound'] )
        log.debug( 'publications solr query result dict["response"]["docs"][0]: %s' % jdict['response']['docs'][0:5] )
        self.pubs_entries = jdict['response']['docs']
        # log.debug( u'self.pubs_entries: %s' % self.pubs_entries )

    def buildPubLists(self):
        """Builds list of publications grouped by type."""
        # log.debug( u'self.pubs_entries: %s' % self.pubs_entries )
        log.debug( 'len( self.pubs_entries ): %s' % len( self.pubs_entries ) )
        corpora_dict = {}; journal_dict = {}; monograph_dict = {}  # temp holders

        # #print len(self.pubs_entries)
        # #print self.pubs_entries.__class__
        # #print str(self.pubs_entries[1:4])

        for entry in self.pubs_entries:  # an entry can contain multiple bibs
            # log.debug( u'entry being processed: %s' % entry )
            ## make separate bib entries

            # #print "\n" + str(entry)

            temp_bibs = []
            last_bib_type = None
            for i, bib_id in enumerate( entry['bib_ids'] ):
                try:
                    last_bib_type = entry['bib_ids_types'][i]  # first should always succeed
                    #print last_bib_type + "; bib_id: " + bib_id + "; i: " + i
                except:
                    pass
                try:
                    bib_title = entry['bib_titles_all'][i]
                except:
                    bib_title = 'title not found for bib_id "%s"' % bib_id
                try:
                    bib_status = entry['status']
                except:
                    bib_status = 'no_status'
                # try:
                #     #only monographs have a single author
                #     if (last_bib_type == 'monograph'):
                #         id_types_list = entry[u'bib_ids_types'] #get the list of id types
                #         monograph_indices_before = [j for j, element in enumerate(id_types_list[0:i]) if element == 'monograph'] #finds the indices for all monographs before this one in the same entry
                #         num_monographs_before = len([id_types_list[k] for k in monograph_indices_before])
                #         num_monographs_index_modifier = num_monographs_before - 1
                #         index = num_monographs_index_modifier + i
                #         bib_author = entry[u'bib_authors'][index]
                #     #journals and corpora have multiple authors
                #     else:
                #         bib_author = u'multiple_authors'
                # except:
                #     bib_author = u'no_author'
                # try:
                #     bib_id = entry[u'bib_ids'][i]
                # except:
                #     try:
                #         bib_id = entry[u'bib_ids'][0] # try again and just use the first bib_id
                #     except:
                #         bib_id = u'no_bib_id'
                temp_bibs.append( {
                    'bib_id': bib_id,
                    'bib_title': bib_title,
                    'bib_type': last_bib_type,
                    'id': entry['id'],  # the inscription_id
                    'status': bib_status
                    # u'bib_author': bib_author,
                    # u'bib_id': bib_id
                    } )
            # log.debug( u'temp_bibs: %s' % temp_bibs )

            # #print len(temp_bibs)
            # #print temp_bibs.__class__
            # #print str(temp_bibs[1:4])


            ## categorize by bib_type
            for bib in temp_bibs:
                ## update master dict
                # self.master_pub_dict[ bib[u'bib_title'] ] = { u'id': bib[u'id'], u'status': bib[u'status'] }
                if bib['bib_title'] in list(self.master_pub_dict.keys()):
                    self.master_pub_dict[ bib['bib_title'] ].append( bib['id'] )
                else:
                    self.master_pub_dict[ bib['bib_title'] ] = [ bib['id'] ]
                ## update type-dicts
                if bib['bib_type'] == 'corpora':
                    if bib['bib_title'] in list(corpora_dict.keys()):
                        corpora_dict[ bib['bib_title'] ].append( bib['id'] )
                    else:
                        corpora_dict[ bib['bib_title'] ] = [ bib['id'] ]
                elif bib['bib_type'] == 'journal':
                    if bib['bib_title'] in list(journal_dict.keys()):
                        journal_dict[ bib['bib_title'] ].append( bib['id'] )
                    else:
                        journal_dict[ bib['bib_title'] ] = [ bib['id'] ]
                elif bib['bib_type'] == 'monograph':
                    # log.debug( u'bib_type is monograph' )
                    if bib['bib_title'] in list(monograph_dict.keys()):
                        monograph_dict[ bib['bib_title'] ].append( bib['id'] )
                    else:
                        monograph_dict[ bib['bib_title'] ] = [ bib['id'] ]

                # log.debug( u'monograph_dict is now: %s' % monograph_dict )
        ## store
        self.corpora_dict = corpora_dict
        self.corpora = sorted( self.corpora_dict.keys() )
        self.journals_dict = journal_dict
        self.journals = sorted( self.journals_dict.keys() )
        self.monographs_dict = monograph_dict
        self.monographs = sorted( self.monographs_dict.keys() )

        # #print ("\n'Classical Attic Tombstones' in self.corpora_dict.keys() " + str('Classical Attic Tombstones' in self.corpora_dict.keys()))
        # print str([j for j, element in enumerate(self.corpora_dict.keys()) if element == 'Classical Attic Tombstones'])
        # print str(self.corpora_dict[('Classical Attic Tombstones')])

        # print ("\n'Classical Attic Tombstones' in self.journals_dict.keys() " + str('Classical Attic Tombstones' in self.journals_dict.keys()))
        # print str([j for j, element in enumerate(self.journals_dict.keys()) if element == 'Classical Attic Tombstones'])
        # print str(self.journals_dict[('Classical Attic Tombstones')])

        # print ("\n'Classical Attic Tombstones' in self.monographs_dict.keys() " + str('Classical Attic Tombstones' in self.monographs_dict.keys()))
        # print str([j for j, element in enumerate(self.monographs_dict.keys()) if element == 'Classical Attic Tombstones'])
        # print str(self.monographs_dict[('Classical Attic Tombstones')])



        # log.debug( u'corpora list before sort: %s' % self.corpora )
        return

    # end class Publications()


class SolrHelper(object):
    default_params = {
        'start': '0',
        'indent': 'on',
        'facet': 'on',
        'facet.mincount': '1',
        'facet.limit':'-1',
        'wt': 'json' }
    solr_url = settings_app.SOLR_URL_BASE

    default_facets = ["condition", "language", "material",
        "object_type", "text_genre", "writing", "status", "char", "name", "fake"]

    null_fields = ["condition", "material","writing","char","name","fake"]

    def __init__(self):
        self.vocab = Vocab()

    def makeSolrQuery(self, q_obj):
        fields = []
        if "notBefore" not in q_obj or "notAfter" not in q_obj:
            # if we have an incomplete date, just skip it
            if "date_type" in q_obj:
                del q_obj["date_type"]
            if "notBefore" in q_obj:
                del q_obj["notBefore"]

            if "notAfter" in q_obj:
                del q_obj["notAfter"]

        elif len(q_obj["notBefore"][0]) == 0 or len(q_obj["notBefore"][0]) == 0:
            if "date_type" in q_obj:
                del q_obj["date_type"]
            if "notBefore" in q_obj:
                del q_obj["notBefore"]
            if "notAfter" in q_obj:
                del q_obj["notAfter"]

        else:
            dtype = q_obj["date_type"][0]
            nb = int(q_obj["notBefore"][0])
            na = int(q_obj["notAfter"][0])
            del q_obj["date_type"]
            del q_obj["notBefore"]
            del q_obj["notAfter"]
            qstring = ""
            if dtype == "inclusive":
                qstring = "(notBefore:[{0} TO {1}] OR notAfter:[{0} TO {1}] OR (notBefore:[* TO {0}] AND notAfter[{1} TO *]) OR (notBefore:[{0} TO *] AND notAfter[* TO {1}]))"
            else:
                qstring = "(notBefore:[{0} TO *] AND notAfter[* TO {1}])"


            fields += [qstring.format(nb, na)]


        for f in q_obj:
            if f.startswith("facet_"):

                if f == "facet_fake":
                    if q_obj[f][0] == 'not_fake':
                        fields += ["NOT (fake:*)"]
                    else:
                        fields += ["(fake:*)"]
                    continue

                if q_obj[f][0] == 'none_value':
                    fields += ["NOT ({0}:*)".format(f[6:])]
                    continue

                fields += ["({0}:{1})".format(f[6:], q_obj[f][0])]
                continue

            if f == "fake":
                if q_obj[f][0] == 'hide':
                    fields = fields + ["NOT (fake:*)"]
                continue

            if f == "status":
                if q_obj[f][0] == "transcription":
                    fields = fields + ["(status:transcription)"]
                elif q_obj[f][0] == "metadata":
                    fields = fields + ["(status:transcription OR status:metadata)"]
                else:
                     fields = fields + ["(status:*)"]
                continue

            values = []
            for v in q_obj[f]:
                if v:
                    values = values + ["{0}:{1}".format(f,v)]

            if values: fields = fields + ["("+(" OR ".join(values))+")"]

        return " AND ".join(fields)

    def add_collection(self, result_list):
        for doc in result_list:
            col_list = []
            if "msid_region" in doc: col_list.append(doc['msid_region'])
            if "msid_settlement" in doc: col_list.append(doc['msid_settlement'])
            if "msid_institution" in doc: col_list.append(doc['msid_institution'])
            if "msid_repository" in doc: col_list.append(doc['msid_repository'])

            doc['collection'] = '.'.join(col_list)

        return result_list

    def query(self, q_obj, params={}, search_form=False):
        q = self.makeSolrQuery(q_obj)
        params = dict(list(params.items()) + list(self.default_params.items()))
        params['facet.mincount'] = "1"
        params['facet.field'] = self.default_facets
        params['facet.query'] = ["NOT {0}:*".format(f) for f in self.null_fields]
        params['q'] = q
        log.debug( 'solr_url, `{}`'.format(self.solr_url) )
        r = requests.get(self.solr_url, params=params)
        log.debug( 'r.url, `{}`'.format(r.url) )
        resp = r.json()
        log.debug( 'resp, ```{}```'.format(pprint.pformat(resp)) )
        # if "error" in resp:
        #     return resp, None, None
        return self.add_collection(resp['response']['docs']), self.facetDisplay(resp['facet_counts'], search_form), q

    def facetDisplay(self, facets, form=False):
        """Make a display dict from a solr facet result, parsing the counts into a dict"""
        facet_displays = dict()
        facet_dict = facets['facet_fields']
        facet_queries = facets['facet_queries']

        def name_key(value):
            if "." in value[0]:
                return (self.vocab[value[0].split(".")[0]].lower(), self.vocab[value[0]].lower())
            else:
                return (self.vocab[value[0]].lower(), value[0].lower())

        sorter = lambda x: -x[1]
        if form:
            sorter = name_key

        for field in facet_dict:
            facet_displays[field] = dict()
            counts = facet_dict[field]
            if field == "fake":
                num = sum([counts[x] for x in range(1, len(counts), 2)])
                li = []
                if num != 0: li += [("fake",num)]
                if facet_queries["NOT fake:*"] != 0: li += [("not_fake",facet_queries["NOT fake:*"])]
                facet_displays["fake"] = li

                continue

            total = 0

            for i in range(0,len(counts), 2):
                f_display = counts[i]
                facet_displays[field][f_display] = counts[i+1]
                total += counts[i+1]

            if "NOT {0}:*".format(field) in facet_queries:
                facet_displays[field]["none_value"] = facet_queries["NOT {0}:*".format(field)]
            facet_displays[field] = sorted(list(facet_displays[field].items()), key=sorter)

        return facet_displays

    def enhance_solr_data( self, solr_data, url_scheme, server_name ):
        """ Adds to dict entries from solr: image-url and item-url. """
        log.debug('starting enhance_solr_data')
        enhanced_list = []
        for entry in solr_data:
            image_url = None
            if 'graphic_name' in list(entry.keys()):
                #image_url = u'%s/%s' % ( settings_app.INSCRIPTIONS_URL_SEGMENT, entry[u'graphic_name'] )
                # log.debug("enhance_solr_data graphic_name", entry['graphic_name'])
                if entry['graphic_name'].startswith('https:') or entry['graphic_name'].startswith('http:'):
                    image_url = entry['graphic_name']
                else:
                    image_url = '%s/%s' % ( settings_app.INSCRIPTIONS_URL_SEGMENT, entry['graphic_name'] )
            
            entry['image_url'] = image_url
            entry['url'] = '%s://%s%s' % ( url_scheme, server_name, reverse('inscription_url', args=(entry['id'],)) )
            enhanced_list.append( entry )
        return enhanced_list

class Vocab(object):
    """Matches controlled values to display values."""
    tax_url = settings_app.DISPLAY_PUBLICATIONS_BIB_URL.replace("titles.xml", "include_taxonomies.xml")

    fieldNames = {
        "condition": "Condition",
        "decoration": "Decoration",
        "fake": "Fake",
        "language": "Language",
        "material": "Material",
        "object_type":"Type of Object",
        "text_genre": "Genre",
        "writing": "Writing",
        "status": "Transcription Status",
        "char": "Special Characters",
        "name": "Names",
        "metadata": "Metadata",
        "transcription": "Fully Transcribed",
        "bib_only": "Citations",
    }

    language_pairs = {
        "grc": "Greek",
        "grc-Latn": "Greek written in Roman characters",
        "grc-Cprt": "Greek written in Cypriot",
        "lat": "Latin",
        "la": "Latin",
        "la-Grek": "Latin written in Greek",
        "lat-Grek":"Latin written in Greek",
        "ett": "Etruscan",
        "xrr": "Raetic",
        "hbo": "Hebrew",
        "phn": "Punic",
        "arc": "Aramaic",
        "ecy": "Eteocypriot",
        "und": "Undecided",
        "zxx": "Non-linguistic",
        "unknown": "Unknown",
        "lat": "Latin",
    }

    others = {
        "not_fake":"Genuine",
        "none_value":"No Value",
    }

    def __init__(self):
        try:
            r = requests.get(self.tax_url)
            self.xml = etree.fromstring(r.content)
            self.control_vals = etree.XPath("//t:category/@xml:id", namespaces={"t":"http://www.tei-c.org/ns/1.0"})(self.xml)
        except Exception as e:
            logging.error(e)
            self.control_vals = []


        self.map = dict()

        for val in self.control_vals:
            display = etree.XPath("//t:category[@xml:id='{0}']/t:catDesc".format(val), namespaces={"t":"http://www.tei-c.org/ns/1.0"})(self.xml)
            if display:
                self.map[val] = display[0].text

        self.map = dict(list(self.map.items()) + list(self.fieldNames.items()) + list(self.language_pairs.items()) + list(self.others.items()))

    def __getitem__(self, i):
        i = i.replace("#", "")
        if i in self.map:
            return self.map[i]
        else:
            return i
