# -*- coding: utf-8 -*-



import collections, logging, pprint
from pathlib import Path

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
        for ( key, val ) in list(item_dct.items()):
            if val != None:
                non_none_keys.append( key )
        self.assertEqual(
            ['grc', 'lat'], non_none_keys
            )

    def test_returned_count( self ):
        count = self.return_tuple[1]
        self.assertEqual(
            2, count
            )

    def test_returned_display_pairs( self ):
        display_pairs = self.return_tuple[2]
        self.assertEqual(
            collections.OrderedDict( [('grc', 'Greek'), ('lat', 'Latin')] ),
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

class CollectionViewSortTest( TestCase ):
    """ Checks docs sorting by ID on collection view. """

    def setUp( self ):
        # Partial data from real docs in the CA Berkeley collection, in a random order
        self.EXAMPLE_DOCS = [
            {'title': 'CA.Berk.UC.HMA.L.8/4286', 'id': 'CA.Berk.UC.HMA.L.8-4286', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '8/4286'},
            {'title': 'CA.Berk.UC.HMA.L.8/4294', 'id': 'CA.Berk.UC.HMA.L.8-4294', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '8/4294'},
            {'title': 'CA.Berk.UC.HMA.L.#97.3.2', 'id': 'CA.Berk.UC.HMA.L.Tmp97.3.2', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '#97.3.2'},
            {'title': 'CA.Berk.HMA.G.8/4985', 'id': 'CA.Berk.UC.HMA.G.8-4985', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '8/4985'},
            {'title': 'CA.Berk.UC.HMA.L.8/4278', 'id': 'CA.Berk.UC.HMA.L.8-4278', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '8/4278'},
            {'title': 'CA.Berk.UC.HMA.L.8/4296', 'id': 'CA.Berk.UC.HMA.L.8-4296', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '8/4296'},
            {'title': 'CA.Berk.UC.HMA.L.8/3125', 'id': 'CA.Berk.UC.HMA.L.8-3125', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '8/3125'},
            {'title': 'CA.Berk.UC.HMA.L.8.71.7767', 'id': 'CA.Berk.UC.HMA.L.8.71.7767', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '8.71.7767'},
            {'title': 'CA.Berk.UC.HMA.L.#97.3.1', 'id': 'CA.Berk.UC.HMA.L.Tmp97.3.1', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '#97.3.1'},
            {'title': 'CA.Berk.UC.HMA.L.8/4285', 'id': 'CA.Berk.UC.HMA.L.8-4285', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '8/4285'}
        ]

    def test_sorting(self):
        # Need to get a collection object, then run getsolrdata
        sorted_doc_list = sorted(self.EXAMPLE_DOCS, key=models.id_sort )
        correct_sorted_doc_list = [
            {'title': 'CA.Berk.UC.HMA.L.8.71.7767', 'id': 'CA.Berk.UC.HMA.L.8.71.7767', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '8.71.7767'},
            {'title': 'CA.Berk.UC.HMA.L.8/3125', 'id': 'CA.Berk.UC.HMA.L.8-3125', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '8/3125'},
            {'title': 'CA.Berk.UC.HMA.L.8/4278', 'id': 'CA.Berk.UC.HMA.L.8-4278', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '8/4278'},
            {'title': 'CA.Berk.UC.HMA.L.8/4285', 'id': 'CA.Berk.UC.HMA.L.8-4285', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '8/4285'},
            {'title': 'CA.Berk.UC.HMA.L.8/4286', 'id': 'CA.Berk.UC.HMA.L.8-4286', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '8/4286'},
            {'title': 'CA.Berk.UC.HMA.L.8/4294', 'id': 'CA.Berk.UC.HMA.L.8-4294', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '8/4294'},
            {'title': 'CA.Berk.UC.HMA.L.8/4296', 'id': 'CA.Berk.UC.HMA.L.8-4296', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '8/4296'},
            {'title': 'CA.Berk.HMA.G.8/4985', 'id': 'CA.Berk.UC.HMA.G.8-4985', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '8/4985'},
            {'title': 'CA.Berk.UC.HMA.L.#97.3.1', 'id': 'CA.Berk.UC.HMA.L.Tmp97.3.1', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '#97.3.1'},
            {'title': 'CA.Berk.UC.HMA.L.#97.3.2', 'id': 'CA.Berk.UC.HMA.L.Tmp97.3.2', 'msid_region': 'CA', 'msid_settlement': 'Berk', 'msid_institution': 'UC', 'msid_repository': 'HMA', 'msid_idno': '#97.3.2'},
        ]

        self.assertEqual(sorted_doc_list, correct_sorted_doc_list)        


class CollectionsAccessibilityRegressionTest( TestCase ):
    """ Checks malformed collection-region data does not render empty links or headings. """

    def test_blank_region_metadata_does_not_render_empty_navigation_or_headings( self ):
        """ Checks blank region values do not produce href="#" links or empty headings. """
        models.FlatCollection.objects.bulk_create(
            [
                models.FlatCollection(
                    collection_code='BROKEN.1',
                    region_code='',
                    region_name='',
                    collection_name='Broken Collection',
                    collection_address='Somewhere',
                    collection_url='https://example.com/broken',
                    collection_description='Broken description',
                ),
                models.FlatCollection(
                    collection_code='RI.TEST.1',
                    region_code='RI',
                    region_name='Rhode Island',
                    collection_name='Rhode Island Collection',
                    collection_address='Providence, RI',
                    collection_url='https://example.com/ri',
                    collection_description='Normal description',
                ),
            ]
        )

        response = self.client.get( '/usep/collections/' )

        self.assertEqual( 200, response.status_code )
        self.assertNotContains( response, 'href="#"' )
        self.assertNotContains( response, '<h3 id=""></h3>', html=True )
        self.assertContains( response, 'href="#ri"' )
        self.assertContains( response, '<h3 id="ri">Rhode Island</h3>', html=True )


class DisplayInscriptionContrastRegressionTest( TestCase ):
    """ Checks inscription heading contrast styling stays above the failure threshold. """

    def test_inscription_heading_color_is_darkened_for_contrast( self ):
        """ Checks translation and commentary headings use the darker local CSS color. """
        response = self.client.get( '/usep/inscription/CA.Berk.UC.HMA.L.8-2330/' )

        self.assertEqual( 200, response.status_code )
        self.assertContains( response, 'usep/css/inscription.css' )

        css_text = Path( __file__ ).with_name( 'static' ).joinpath( 'usep/css/inscription.css' ).read_text( encoding='utf-8' )
        self.assertIn( 'color:#3f6662;', css_text )
