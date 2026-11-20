from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse
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
                searches = [call for call in self.http_get.call_args_list if call.args == (SolrHelper.solr_url,)]
                self.assertEqual([call.kwargs['params']['q'] for call in searches], [expected])

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
