from django import template
from usep_app import models

register = template.Library()

v = models.Vocab()

@register.filter( name='tax' )
def tax( name ):
  return v[name]

@register.filter( name='era' )
def era(i):
	# there is no year 0
	if i == 0: i = 1

	if i < 0:
		return "{0} BCE".format(-i)
	else:
		return "{0} CE".format(i)