# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import collections, logging, pprint

from django.test import TestCase
from usep_app import models


log = logging.getLogger(__name__)
TestCase.maxDiff = None


class SeparateIntoLanguagesTest( TestCase ):
    """ Tests models.separate_into_languages()
        TODO- create libs.view_collection_helper.py, and move separate_into_languages() there. """

    def setUp(self):
        self.ENHANCED_SOLR_DOCS = [
            {
                '_version_': 1529799273867116544,
                'bib_ids': ['Festschrift'],
                'condition': '#complete.intact',
                'condition_desc': ['some weathering and chipping of lid'],
                'decoration': 'unknownDec',
                'decoration_desc': ['no photo'],
                'id': 'CA.SS.HHM.L.529.9.411',
                'image_url': None,
                'language': ['lat'],
                'material': '#stone.limestone',
                'material_desc': ['Limestone sarcophagus'],
                'msid_idno': '529.9.411',
                'msid_institution': 'HHM',
                'msid_region': 'CA',
                'msid_settlement': 'SS',
                'notAfter': 300,
                'notBefore': 200,
                'object_type': '#sarcophagus',
                'status': 'metadata',
                'text_genre': '#funerary.epitaph',
                'text_genre_desc': ['Epitaph of C. Insteius Maximus'],
                'title': 'CA.SS.HHM.L.529.9.411',
                'url': 'http://127.0.0.1:8000/usep/inscription/CA.SS.HHM.L.529.9.411/',
                'writing': '#impressed.inscribed.carved'
            },
            {
                '_version_': 1529799273672081408,
                'bib_ids': ['unpub'],
                'condition': '#complete.intact',
                'condition_desc': ['some repairs, some weathering possibly obscuring a single line of text on one end'],
                'decoration': 'unknownDec',
                'decoration_desc': ['no photo'],
                'id': 'CA.SS.HHM.GL.529.9.413',
                'image_url': None,
                'language': ['grc', 'lat'],
                'material': '#stone.marble',
                'material_desc': ['Marble sarcophagus'],
                'msid_idno': 'CA.SS.HHM.GL.529.9.413',
                'msid_institution': 'HHM',
                'msid_region': 'CA',
                'msid_settlement': 'SS',
                'notAfter': 500,
                'notBefore': 300,
                'object_type': '#sarcophagus',
                'status': 'metadata',
                'text_genre': '#funerary.epitaph',
                'text_genre_desc': ['Epitaph (in Greek) and funerary sentiment (in Latin) of a Christian Nikolaos Blasios ?'],
                'title': 'CA.SS.HHM.GL.529.9.413',
                'url': 'http://127.0.0.1:8000/usep/inscription/CA.SS.HHM.GL.529.9.413/',
                'writing': '#impressed.inscribed.carved'
            }
        ]
        self.return_tuple = models.separate_into_languages( self.ENHANCED_SOLR_DOCS )
        ## end setUp()

    def test_returned_items( self ):
        """ Checks items-element of returned tuple. """
        item_dct = self.return_tuple[0]

        self.assertEqual(
            collections.OrderedDict, type( item_dct )
            )

        self.assertEqual(
            ['grc', 'grc-Latn', 'grc-Cprt', 'lat', 'la', 'la-Grek', 'lat-Grek', 'arc', 'ecy', 'ett', 'hbo', 'phn', 'xrr', 'zxx', 'und', 'unknown'],
            list(item_dct.keys())
            )

        non_none_keys = []
        for ( key, val ) in item_dct.items():
            if val != None:
                non_none_keys.append( key )
        self.assertEqual(
            [u'grc', u'lat'], non_none_keys
            )

    def test_returned_count( self ):
        count = self.return_tuple[1]
        self.assertEqual(
            2, count
            )

    def test_returned_display_pairs( self ):
        display_pairs = self.return_tuple[2]
        self.assertEqual(
            collections.OrderedDict( [(u'grc', u'Greek'), (u'lat', u'Latin')] ),
            display_pairs
            )

    ## end class SeparateIntoLanguagesTest()


class UrlTest( TestCase ):
    """ Checks urls. """

    def test_search(self):
        """ Checks '/usep/search/results/' """
        response = self.client.get( '/usep/search/results/?text=CA.Berk.UC.HMA' )
        self.assertEqual( bytes, type(response.content) )  # means bytes
        self.assertEqual( 200, response.status_code )  # permanent redirect
        self.assertTrue(  b'Inscription Results' in response.content )
