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
__version__ = '1.3.2'

from . import utils as utils
from .client import Client as Client, LinkedRolesOAuth2 as LinkedRolesOAuth2
from .enums import OAuth2Scopes as OAuth2Scopes, RoleMetadataType as RoleMetadataType
from .errors import (
    HTTPException as HTTPException,
    InternalServerError as InternalServerError,
    LinkedRoleError as LinkedRoleError,
    NotFound as NotFound,
    RateLimited as RateLimited,
    ScopeMissing as ScopeMissing,
    Unauthorized as Unauthorized,
)
from .role import (
    RoleConnection as RoleConnection,
    RoleMetadata as RoleMetadata,
    RoleMetadataRecord as RoleMetadataRecord,
)
from .user import User as User
