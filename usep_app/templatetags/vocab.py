from functools import lru_cache

from django import template

from usep_app import models

register = template.Library()


@lru_cache(maxsize=1)
def display_vocabulary() -> models.Vocab:
    """
    Loads the vocabulary the first time a template displays a catalog label.
    Called by: tax().
    """
    return models.Vocab()


@register.filter(name='tax')
def tax(name: str) -> str:
    """
    Looks up the catalog label for a stored value.
    Called by: Django's template engine.
    """
    return display_vocabulary()[name]


@register.filter(name='era')
def era(year: int) -> str:
    """
    Displays a signed year, using 1 CE for a stored year of zero.
    Called by: Django's template engine.
    """
    return f'{-year} BCE' if year < 0 else f'{year or 1} CE'
