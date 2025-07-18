from django import template
from django.utils.http import urlquote_plus

"""I couldn't find a built-in template-filter for this"""


register = template.Library()

@register.filter( name='insert_pluses' )
def insert_pluses( name ):
  try:
    return urlquote_plus( name )
  except Exception as e:
    return ''
