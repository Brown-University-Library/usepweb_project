from __future__ import annotations

import re
import unicodedata

from django.core.exceptions import ValidationError

FORM_FILTERS = ('text_genre', 'object_type', 'material', 'language', 'writing', 'condition', 'char')
FACET_FIELDS = (
    'condition',
    'language',
    'material',
    'object_type',
    'text_genre',
    'writing',
    'status',
    'char',
    'name',
    'fake',
)
NULL_FIELDS = ('condition', 'material', 'writing', 'char', 'name', 'fake')
TAXONOMY_FIELDS = {'condition', 'material', 'object_type', 'text_genre', 'writing'}
DATE_KEYS = {'notBefore', 'notAfter', 'date_type'}
FACET_FIELD_BY_KEY = {f'facet_{field}': field for field in FACET_FIELDS}
SEARCH_KEYS = {'text', 'fake', 'status', *DATE_KEYS, *FORM_FILTERS, *FACET_FIELD_BY_KEY}

STATUS_QUERIES = {
    'transcription': '(status:transcription)',
    'metadata': '(status:transcription OR status:metadata)',
    'bib_only': '(status:*)',
}
CHOICES = {
    'date_type': {'inclusive', 'exclusive'},
    'status': set(STATUS_QUERIES),
    'facet_status': set(STATUS_QUERIES),
    'fake': {'include', 'hide'},
    'facet_fake': {'fake', 'not_fake'},
}
MAX_QUERY_BYTES = 8192
MAX_VALUES = 256
MAX_TEXT_LENGTH = 512
MAX_FILTER_LENGTH = 128


def validate_fields(params: dict[str, list[str]]) -> None:
    """
    Checks field names, fixed choices, and the size of the submitted values.
    Called by: build_search_query().
    """
    if params.keys() - SEARCH_KEYS:
        raise ValidationError('This search contains an unrecognized field.')
    if sum(len(values) for values in params.values()) > MAX_VALUES:
        raise ValidationError('Please choose fewer search filters.')
    for key, values in params.items():
        field = FACET_FIELD_BY_KEY.get(key, key)
        if not values or (key not in FORM_FILTERS and key not in FACET_FIELD_BY_KEY and len(values) != 1):
            raise ValidationError('Please enter a single value for each search control.')
        for value in values:
            limit = MAX_TEXT_LENGTH if key == 'text' else MAX_FILTER_LENGTH
            if len(value) > limit or any(not char.isprintable() and unicodedata.category(char) != 'Zs' for char in value):
                raise ValidationError('Please shorten the search or remove invisible characters.')
            if key in CHOICES and value not in CHOICES[key] and not (key in FACET_FIELD_BY_KEY and not value.strip()):
                raise ValidationError('Please select one of the available search options.')
            stripped = value.strip()
            if field == 'language' and stripped and not re.fullmatch(r'[A-Za-z]{1,8}(?:-[A-Za-z0-9]{1,8})*', stripped):
                raise ValidationError('Please select a language from the search filters.')
            if field in TAXONOMY_FIELDS and stripped and not re.fullmatch(r'#?[\w.-]+(?: +#?[\w.-]+)*', stripped):
                raise ValidationError('Please select a value from the search filters.')


def date_clause(params: dict[str, list[str]]) -> str:
    """
    Builds an overlapping or fully contained range using the two years entered on the form.
    Called by: build_search_query().
    """
    start = params.get('notBefore', [''])[0].strip()
    end = params.get('notAfter', [''])[0].strip()
    if not start and not end:
        return ''
    if not start or not end:
        raise ValidationError('Enter both years for a date range, or leave both blank.')
    if not all(re.fullmatch(r'[+-]?[0-9]{1,4}', value) for value in (start, end)):
        raise ValidationError('Enter whole years between -1000 and 1000. Use a negative year for BCE.')
    first, last = int(start), int(end)
    if not -1000 <= first <= last <= 1000:
        raise ValidationError('Enter years from -1000 to 1000, with the earlier year first.')
    if params.get('date_type', ['inclusive'])[0] == 'exclusive':
        return f'(notBefore:[{first} TO *] AND notAfter:[* TO {last}])'
    return f'(notBefore:[* TO {last}] AND notAfter:[{first} TO *])'


def literal(value: str) -> str:
    """
    Keeps ordinary words readable and quotes other values as literal Solr terms.
    Called by: filter_clause(), build_search_query().
    """
    if re.fullmatch(r'[\w.]+', value) and value not in {'AND', 'OR', 'NOT'}:
        return value
    escaped = value.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def filter_clause(key: str, values: list[str]) -> str:
    """
    Combines form selections with OR and uses the first nonblank value from a results-page filter.
    Called by: build_search_query().
    """
    field = FACET_FIELD_BY_KEY.get(key, key)
    if key == 'facet_fake':
        return 'NOT (fake:*)' if values[0] == 'not_fake' else '(fake:*)'
    selected = [value.strip() for value in values if value.strip()]
    if key in FACET_FIELD_BY_KEY:
        selected = selected[:1]
    if not selected:
        return ''

    clauses = []
    for value in selected:
        if value == 'none_value' and field in NULL_FIELDS:
            if len(selected) == 1:
                return f'NOT ({field}:*)'
            clauses.append(f'(*:* AND NOT ({field}:*))')
        else:
            clauses.append(f'{field}:{literal(value)}')
    return '(' + ' OR '.join(clauses) + ')'


def build_search_query(params: dict[str, list[str]]) -> str:
    """
    Builds the Solr expression for the public search controls after checking the submitted fields.
    Called by: SolrHelper.makeSolrQuery().
    """
    validate_fields(params)
    clauses = [date_clause(params)]
    for key, values in params.items():
        if key in FORM_FILTERS or key in FACET_FIELD_BY_KEY:
            clauses.append(filter_clause(key, values))
        elif key == 'status':
            clauses.append(STATUS_QUERIES[values[0]])
        elif key == 'fake' and values[0] == 'hide':
            clauses.append('NOT (fake:*)')
        elif key == 'text' and values[0].strip():
            words = [f'text:{literal(word)}' for word in values[0].split()]
            clauses.append('(' + ' '.join(words) + ')')
    return ' AND '.join(clause for clause in clauses if clause)
