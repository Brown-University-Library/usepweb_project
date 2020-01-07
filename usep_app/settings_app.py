# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os


DOCUMENTATION_URL = u'https://github.com/Brown-University-Library/usepweb_project/blob/master/README.md'

LOGIN_URL = unicode( os.environ['USEPWEB__LOGIN_URL'] )

SOLR_URL_BASE = unicode( os.environ['USEPWEB__SOLR_URL_BASE'] )

DISPLAY_PUBLICATIONS_BIB_URL = unicode( os.environ['USEPWEB__DISPLAY_PUBLICATIONS_BIB_URL'] )
DISPLAY_PUBLICATIONS_XSL_URL = unicode( os.environ['USEPWEB__DISPLAY_PUBLICATIONS_XSL_URL'] )  # views.publications()

INSCRIPTIONS_URL_SEGMENT = unicode( os.environ['USEPWEB__INSCRIPTIONS_URL_SEGMENT'] )

DISPLAY_INSCRIPTION_XML_URL_PATTERN = unicode( os.environ['USEPWEB__DISPLAY_INSCRIPTION_XML_URL_PATTERN'] )
DISPLAY_INSCRIPTION_XSL_URL = unicode( os.environ['USEPWEB__DISPLAY_INSCRIPTION_XSL_URL'] )
DISPLAY_INSCRIPTION_SAXONCE_FILE_URL = unicode( os.environ['USEPWEB__DISPLAY_INSCRIPTION_SAXONCE_FILE_URL'] )
DISPLAY_INSCRIPTION_XIPR_URL = unicode( os.environ['USEPWEB__DISPLAY_INSCRIPTION_XIPR_URL'] )

REINDEX_ALL_URL = unicode( os.environ['USEPWEB__REINDEX_ALL_URL'] )
