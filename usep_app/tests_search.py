from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse
from lxml import html
from requests.exceptions import HTTPError

from usep_app.models import SolrHelper


class SearchResultsTest(SimpleTestCase):
    def setUp(self) -> None:
        """
        Sets up local replies for the vocabulary and search requests.
        Called by: Django's test runner.
        """
        get = patch('usep_app.models.requests.get')
        self.http_get = get.start()
        self.addCleanup(get.stop)
        self.http_get.return_value.content = b'<taxonomy/>'
        self.url = reverse('search_results_url')

    def solr_queries(self) -> list[str]:
        """
        Returns the search queries sent to Solr during the test.
        Called by: test_blank_condition_preserves_other_search_terms(), test_name_filter_link_keeps_search(),
        test_year_range_modes_keep_signed_years().
        """
        return [call.kwargs['params']['q'] for call in self.http_get.call_args_list if call.args == (SolrHelper.solr_url,)]

    def test_search_form_offers_languages_from_the_index(self) -> None:
        """
        Checks that readers can select multiple languages from the choices returned by Solr.
        """
        fields = {
            'language': ['lat', 3, 'grc', 2],
            'text_genre': [],
            'object_type': [],
            'material': [],
            'writing': [],
            'condition': [],
            'char': [],
        }
        self.http_get.return_value.json.return_value = {
            'response': {'docs': []},
            'facet_counts': {'facet_fields': fields, 'facet_queries': {}},
        }
        response = self.client.get(reverse('search_url'))
        self.assertEqual(response.status_code, 200)
        options = html.fromstring(response.content).xpath('//form//select[@name="language" and @multiple]/option')
        self.assertEqual(
            [(option.get('value'), option.text_content().strip()) for option in options],
            [('grc', 'Greek'), ('lat', 'Latin')],
        )

    def test_name_filter_link_keeps_search(self) -> None:
        """
        Checks that following a name filter keeps the original text and both selected languages.
        """
        self.http_get.return_value.json.return_value = {
            'response': {'docs': [{'id': 'TEST.1'}]},
            'facet_counts': {'facet_fields': {'name': ['Julia', 1]}, 'facet_queries': {}},
        }
        response = self.client.get(self.url, {'text': 'λίθος', 'language': ['grc', 'lat']})
        self.assertEqual(response.status_code, 200)
        links = html.fromstring(response.content).xpath('//a[normalize-space(.)="Julia (1)"]/@href')
        self.assertEqual(len(links), 1)
        filtered = self.client.get(links[0])
        self.assertContains(filtered, 'TEST.1')

        original, refined = self.solr_queries()
        for query in (original, refined):
            self.assertRegex(query, r'text:"?λίθος\b')
            self.assertRegex(query, r'language:"?grc"? OR language:"?lat\b')
        self.assertNotIn('Julia', original)
        self.assertRegex(refined, r'name:"?Julia\b')

    def test_year_range_modes_keep_signed_years(self) -> None:
        """
        Checks that both date modes carry signed years to Solr and display the dates of a returned inscription.
        """
        self.http_get.return_value.json.return_value = {
            'response': {'docs': [{'id': 'TEST.1', 'notBefore': -25, 'notAfter': 10}]},
            'facet_counts': {'facet_fields': {}, 'facet_queries': {}},
        }
        for mode in ('inclusive', 'exclusive'):
            with self.subTest(mode=mode):
                response = self.client.get(self.url, {'date_type': mode, 'notBefore': '-100', 'notAfter': '50'})
                self.assertContains(response, 'Between 25 BCE and 10 CE')

        inclusive, exclusive = self.solr_queries()
        for query in (inclusive, exclusive):
            self.assertIn('-100', query)
            self.assertIn('50', query)
        self.assertNotEqual(inclusive, exclusive)

    def test_blank_condition_preserves_other_search_terms(self) -> None:
        """
        Checks that a blank condition produces the same results query as omitting it.
        """
        self.http_get.return_value.json.return_value = {
            'response': {'docs': [{'id': 'TEST.1'}]},
            'facet_counts': {'facet_fields': {}, 'facet_queries': {}},
        }
        terms = {
            'date_type': 'inclusive',
            'notBefore': '',
            'notAfter': '',
            'facet_name': 'Julia',
            'fake': 'hide',
            'status': 'transcription',
            'text': 'stone',
        }
        expected = '(name:Julia) AND NOT (fake:*) AND (status:transcription) AND (text:stone)'
        for condition in ({}, {'facet_condition': ''}, {'facet_condition': '  '}):
            with self.subTest(condition=condition):
                self.http_get.reset_mock()
                response = self.client.get(self.url, {**terms, **condition})
                self.assertContains(response, 'TEST.1')
                self.assertEqual(self.solr_queries(), [expected])

    def test_no_matches(self) -> None:
        """
        Checks that a valid search with no matches still displays the usual results page.
        """
        self.http_get.return_value.json.return_value = {
            'response': {'docs': []},
            'facet_counts': {'facet_fields': {}, 'facet_queries': {}},
        }
        response = self.client.get(self.url, {'text': 'stone'})
        self.assertContains(response, 'No Results')

    def test_selected_facets(self) -> None:
        """
        Checks repeated filters, the explicit No Value choice, and all forgery filter choices.
        """
        helper = SolrHelper()
        cases = [
            ('facet_name', ['', 'Julia', 'Marcus'], '(name:Julia)'),
            ('facet_name', ['Marcus', 'Julia'], '(name:Marcus)'),
            ('facet_condition', ['none_value'], 'NOT (condition:*)'),
            ('facet_fake', [''], '(fake:*)'),
            ('facet_fake', ['fake'], '(fake:*)'),
            ('facet_fake', ['not_fake'], 'NOT (fake:*)'),
        ]
        for field, values, expected in cases:
            with self.subTest(field=field, values=values):
                self.assertEqual(helper.makeSolrQuery({field: values}), expected)

    def test_rejected_query(self) -> None:
        """
        Checks that a rejected search explains the problem and links back to the search form.
        """
        reply = self.http_get.return_value
        reply.status_code = 400
        reply.raise_for_status.side_effect = HTTPError(response=reply)
        response = self.client.get(self.url, {'text': 'stone'})
        self.assertContains(response, 'Please check your search terms and filters.', status_code=400)
        self.assertContains(response, f'<a href="{reverse("search_url")}">Back to search</a>', status_code=400, html=True)
        self.assertNotContains(response, 'No Results', status_code=400)
        reply.json.assert_not_called()

    def test_service_failure(self) -> None:
        """
        Checks that a Solr outage still reaches Django's server error handler.
        """
        reply = self.http_get.return_value
        reply.status_code = 503
        reply.raise_for_status.side_effect = HTTPError(response=reply)
        self.client.raise_request_exception = False
        response = self.client.get(self.url, {'text': 'stone'})
        self.assertEqual(response.status_code, 500)
