from django import template
from urllib.parse import quote_plus

"""I couldn't find a built-in template-filter for this"""


register = template.Library()

@register.filter( name='insert_pluses' )
def insert_pluses( name ):
  try:
    return quote_plus( name )
  except Exception as e:
    return ''
