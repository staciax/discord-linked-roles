"""
Discord Linked Roles OAuth2 Client
~~~~~~~~~~~~~~~~~~~
A basic wrapper for the Discord Linked Roles OAuth2 API.
:copyright: (c) 2023-present staciax
:license: MIT, see LICENSE for more details.
"""

__title__ = 'linked_roles'
__author__ = 'staciax'
__license__ = 'MIT'
__copyright__ = 'Copyright 2023-present staciax'
__version__ = '1.3.0'

from . import utils as utils
from .client import *
from .enums import *
from .errors import *
from .role import *
from .user import *
