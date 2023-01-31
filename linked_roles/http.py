# Copyright (c) 2023-present staciax
# Copyright (c) 2015-present Rapptz
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from typing import TYPE_CHECKING, Any, ClassVar, Coroutine, Dict, List, Mapping, Optional, Tuple, TypedDict, TypeVar, Union
from urllib.parse import quote as _uriquote, urlencode

import aiohttp

from . import utils
from .enums import OAuth2Scopes
from .errors import HTTPException, InternalServerError, NotFound, RateLimited, ScopeMissing, Unauthorized

if TYPE_CHECKING:
    T = TypeVar('T')
    Response = Coroutine[Any, Any, T]

__all__: Tuple[str, ...] = ('HTTPClient',)

_log = logging.getLogger(__name__)

MISSING = utils.MISSING


class User(TypedDict):
    id: str
    username: str
    discriminator: str
    avatar: Optional[str]
    bot: Optional[bool]
    system: Optional[bool]
    mfa_enabled: Optional[bool]
    banner: Optional[str]
    accent_color: Optional[int]
    locale: Optional[str]
    verified: Optional[bool]
    email: Optional[str]
    flags: Optional[int]
    premium_type: Optional[int]
    public_flags: Optional[int]


class OAuth2TokenResponse(TypedDict):
    access_token: str
    refresh_token: str
    expires_in: int


class RoleMetadata(TypedDict):
    name: str
    description: str
    name_localizations: Optional[Dict[str, str]]
    description_localizations: Optional[Dict[str, str]]


class UserRoleConnection(TypedDict):
    platform_name: str
    platform_username: str
    metadata: Dict[str, Any]


class AppRoleConnectionMetadataRecord(TypedDict):
    type: int
    key: str
    name: str
    description: str
    name_localizations: Optional[Dict[str, str]]
    description_localizations: Optional[Dict[str, str]]


def validate_redirect_url(url: Optional[str]) -> Optional[str]:
    if url is not None:
        if url.startswith('localhost'):
            return 'http://' + url
        match = re.match(r'https?://.+', url)
        if not match:
            raise ValueError(f'{url!r} must be a valid http or https url')
        return url
    return None


# HTTPClient, Route inspired by discord.py
# url: https://github.com/Rapptz/discord.py/blob/master/discord/http.py


class Route:

    """Represents an HTTP route."""

    BASE: ClassVar[str] = 'https://discord.com/api/v10'

    def __init__(
        self,
        method: str,
        path: str,
        verify: bool = False,
        **parameters: Any,
    ) -> None:
        self.method = method
        self.path = path
        self.verify = verify
        self.parameters = parameters

        url = self.BASE + self.path

        if parameters:

            url = url.format_map({k: _uriquote(v) if isinstance(v, str) else v for k, v in parameters.items()})

        self.url: str = url


class HTTPClient:

    """Represents an HTTP client for interacting with the Discord API."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client_id: str,
        client_secret: Optional[str],
        redirect_uri: Optional[str],
        scopes: Tuple[str, ...] = (),
        state: Optional[str] = None,
        proxy: Optional[str] = None,
        proxy_auth: Optional[aiohttp.BasicAuth] = None,
        token: Optional[str] = None,
    ) -> None:
        if OAuth2Scopes.identify not in scopes:
            _log.warning('You must specify the identify scope.')
        if OAuth2Scopes.role_connection_write not in scopes:
            _log.warning('You must specify the role_connection_write scope.')
        self.loop: asyncio.AbstractEventLoop = loop
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = validate_redirect_url(redirect_uri)
        self.scopes = scopes
        self.state = state
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self.token = token
        self._session: aiohttp.ClientSession = MISSING

    async def request(self, route: Route, **kwargs: Any) -> Any:
        method = route.method
        url = route.url
        headers = kwargs.pop('headers', {})
        kwargs['verify_ssl'] = route.verify

        response: Optional[aiohttp.ClientResponse] = None
        data: Optional[Union[Dict[str, Any], str]] = None

        for tries in range(5):
            try:
                async with self._session.request(
                    method, url, headers=headers, proxy=self.proxy, proxy_auth=self.proxy_auth, **kwargs
                ) as response:
                    _log.debug('%s %s with %s has returned %s', method, url, kwargs.get('data'), response.status)
                    data = await utils.json_or_text(response)
                    if 300 > response.status >= 200:
                        _log.debug('%s %s has received %s', method, url, data)
                        return data

                    if response.status == 429:
                        if not response.headers.get('Via') or isinstance(data, str):
                            # Banned by Cloudflare more than likely.
                            raise HTTPException(response, data)
                        # We are being rate limited
                        raise RateLimited(response, data)

                    if response.status == 401:
                        raise Unauthorized(response, data)
                    elif response.status == 404:
                        raise NotFound(response, data)
                    elif response.status >= 500:
                        raise InternalServerError(response, data)

            except OSError as e:
                # Connection reset by peer
                if tries < 4 and e.errno in (54, 10054):
                    await asyncio.sleep(1 + tries * 2)
                    continue
                raise

        if response is not None:
            # We've run out of retries, raise.
            if response.status >= 500:
                raise InternalServerError(response, data)

            raise HTTPException(response, data)

        raise RuntimeError('Unreachable code in HTTP handling')

    async def close(self) -> None:
        if self._session is not MISSING:
            await self._session.close()

    async def start(self) -> None:
        self._session = aiohttp.ClientSession()

    def clear(self) -> None:
        if self._session and self._session.closed:
            self._session = MISSING

    def get_oauth_url(self) -> str:
        state = self.state or uuid.uuid4().hex
        url = 'https://discord.com/api/oauth2/authorize'
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.scopes),
            'prompt': 'consent',
            'state': state,
        }
        return url + '?' + urlencode(params)

    def get_oauth2_token(self, code: str) -> Response[OAuth2TokenResponse]:
        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        return self.request(Route('POST', '/oauth2/token'), data=payload, headers=headers)

    def refresh_oauth2_token(self, refresh_token: str) -> Response[OAuth2TokenResponse]:
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        return self.request(Route('POST', '/oauth2/token'), data=payload, headers=headers)

    def get_user(self, access_token: str) -> Response[User]:

        if OAuth2Scopes.identify not in self.scopes:
            raise ScopeMissing('identify')

        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {access_token}'}
        return self.request(Route('GET', '/users/@me'), headers=headers)

    def get_application_role_connection_metadata_records(self) -> Response[List[AppRoleConnectionMetadataRecord]]:
        r = Route('GET', '/applications/{application_id}/role-connections/metadata', application_id=self.client_id)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bot {self.token}',
        }
        return self.request(r, headers=headers)

    def put_application_role_connection_metadata(
        self, payload: List[RoleMetadata]
    ) -> Response[List[AppRoleConnectionMetadataRecord]]:
        r = Route('PUT', '/applications/{application_id}/role-connections/metadata', application_id=self.client_id)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bot {self.token}',
        }
        return self.request(r, json=payload, headers=headers)

    def get_user_application_role_connection(self, access_token: str) -> Response[UserRoleConnection]:

        if OAuth2Scopes.role_connection_write not in self.scopes:
            raise ScopeMissing('role_connection_write')

        r = Route('GET', '/users/@me/applications/{application_id}/role-connection', application_id=self.client_id)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        return self.request(r, headers=headers)

    def put_user_application_role_connection(
        self, access_token: str, payload: Mapping[str, Any]
    ) -> Response[UserRoleConnection]:

        if OAuth2Scopes.role_connection_write not in self.scopes:
            raise ScopeMissing('role_connection_write')

        r = Route('PUT', '/users/@me/applications/{application_id}/role-connection', application_id=self.client_id)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        return self.request(r, json=payload, headers=headers)
