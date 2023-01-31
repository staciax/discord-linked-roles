# Copyright (c) 2023-present staciax
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, Union

import aiohttp

from .errors import Unauthorized
from .http import HTTPClient
from .oauth2 import OAuth2Token
from .role import RoleConnection, RoleMetadataRecord
from .user import User
from .utils import MISSING

__all__: Tuple[str, ...] = ('LinkedRolesOAuth2',)

_log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from datetime import datetime
    from types import TracebackType

    from typing_extensions import Self

    RoleMetadataRecordType = Union[int, bool, datetime]

# -- from discord.py
# link: https://github.com/Rapptz/discord.py/blob/9ea6ee8887b65f21ccc0bcf013786f4ea61ba608/discord/client.py#L111
class _LoopSentinel:
    __slots__ = ()

    def __getattr__(self, attr: str) -> None:
        msg = (
            'loop attribute cannot be accessed in non-async contexts. '
            'Consider using either an asynchronous main function and passing it to asyncio.run or '
        )
        raise AttributeError(msg)


_loop: Any = _LoopSentinel()

# --


class LinkedRolesOAuth2:
    """
    A client for the Linked Roles API.

    Parameters
    ----------
    client_id : :class:`str`
        The client ID of the application.
    client_secret : Optional[:class:`str`]
        The client secret of the application.
    redirect_uri : Optional[:class:`str`]
        The redirect URI of the application.
    token :
        The token of the application.
    scopes : Tuple[:class:`str`, ...]
        The scopes of the application.
    state : Optional[:class:`str`]
        The state of the application.
    proxy : Optional[:class:`str`]
        The proxy of the application.
    proxy_auth : Optional[:class:`aiohttp.BasicAuth`]
        The proxy auth of the application.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        token: Optional[str] = None,
        scopes: Tuple[str, ...] = (),
        state: Optional[str] = None,
        proxy: Optional[str] = None,
        proxy_auth: aiohttp.BasicAuth = MISSING,
    ) -> None:
        self.application_id = client_id
        self.loop: asyncio.AbstractEventLoop = _loop
        self._http = HTTPClient(
            loop=self.loop,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=scopes,
            state=state,
            proxy=proxy,
            proxy_auth=proxy_auth,
            token=token,
        )
        self._role_metadata: Dict[str, RoleMetadataRecord] = {}
        self._users: Dict[int, User] = {}
        self._role_metadat_is_fetched: bool = False
        self._is_closed: bool = False

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        if not self._is_closed:
            await self.close()

    async def start(self):
        """
        Starts the client.
        """
        loop = asyncio.get_running_loop()
        self.loop = loop
        self._http.loop = loop
        await self._http.start()
        if self._http.token is not None:
            role_connections_records = await self._http.get_application_role_connection_metadata_records()
            for record in role_connections_records:
                role_metadata = RoleMetadataRecord.from_dict(record)
                self._role_metadata[role_metadata.key] = role_metadata
            self._role_metadat_is_fetched = True

    async def close(self) -> None:
        """
        Closes the client.
        """
        if self._is_closed:
            return
        self._is_closed = True
        await self._http.close()

    def clear(self) -> None:
        """
        Clears the client.
        """
        self._role_metadata.clear()
        self._users.clear()
        self._role_metadat_is_fetched = False
        self._http.clear()

    def is_closed(self) -> bool:
        """
        Whether the client is closed.
        Returns
        -------
        :class:`bool`
            Whether the client is closed.
        """
        return self._is_closed

    def is_role_metadata_fetched(self) -> bool:
        """
        Whether the role metadata is fetched.
        Returns
        -------
        :class:`bool`
            Whether the role metadata is fetched.
        """
        return self._role_metadat_is_fetched

    def get_oauth_url(self) -> str:
        """
        Gets the OAuth URL.
        Returns
        -------
        :class:`str`
            The OAuth URL.
        """
        return self._http.get_oauth_url()

    async def get_access_token(self, code: str) -> OAuth2Token:
        """
        Gets the access token.
        Parameters
        ----------
        code : :class:`str`
            The code.
        Returns
        -------
        :class:`OAuth2Token`
            The OAuth2 token.
        """
        data = await self._http.get_oauth2_token(code)
        return OAuth2Token(self, data)

    async def register_role_metadata(
        self, records: Tuple[RoleMetadataRecord, ...], force: bool = False
    ) -> List[RoleMetadataRecord]:
        """
        Registers the role metadata.
        Parameters
        ----------
        records : Tuple[:class:`RoleMetadataRecord`, ...]
            The role metadata records.
        force : Optional[:class:`bool`]
            Whether to force register the role metadata.
        Returns
        -------
        :class:List[:class:`RoleMetadataRecord`]
            The registered role metadata records.
        """
        payload = []
        for record in records:
            if record.key not in self._role_metadata and not force:
                raise ValueError(f'Role metadata with key {record.key} already exists')
            payload.append(record.to_dict())
            self._role_metadata[record.key] = record
        data = await self._http.put_application_role_connection_metadata(payload)
        return [RoleMetadataRecord.from_dict(record) for record in data]

    def get_role_metadata(self, key: str) -> Optional[RoleMetadataRecord]:
        """
        Gets the role metadata by it's key.
        Parameters
        ----------
        key : :class:`str`
            The key.
        Returns
        -------
        Optional[:class:`RoleMetadataRecord`]
            The role metadata record.
        """
        return self._role_metadata.get(key)

    async def fetch_user(self, token: OAuth2Token) -> Optional[User]:
        """
        Fetches the user.
        Parameters
        ----------
        token : :class:`OAuth2Token`
            The OAuth2 token.
        Returns
        -------
        Optional[:class:`User`]
            The user.
        """
        data = await self._http.get_user(token.access_token)
        if data is None:
            return None
        user = User(self, data, token)
        self._users[int(user.id)] = user
        return user

    def get_user(self, id: int) -> Optional[User]:
        """
        Gets the user by it's id.
        Parameters
        ----------
        id : Union[:class:`str`, :class:`int`]
            The user id.
        Returns
        -------
        Optional[:class:`User`]
            The user.
        """
        return self._users.get(id)

    async def is_authenticated(self, token: Union[OAuth2Token, str]) -> bool:
        """
        Checks if the user is authenticated.
        Parameters
        ----------
        token : Union[:class:`OAuth2Token`, :class:`str`]
            The OAuth2 token.
        Returns
        -------
        :class:`bool`
            Whether the user is authenticated.
        """
        access_token = token.access_token if isinstance(token, OAuth2Token) else token
        try:
            await self._http.get_user(access_token)
        except Unauthorized:
            return False
        else:
            return True

    async def on_user_application_role_connection_update(
        self,
        user: User,
        before: RoleConnection,
        after: RoleConnection,
    ) -> None:
        """
        Called when a user's application role connection is updated.
        Parameters
        ----------
        user : :class:`User`
            The user.
        before : :class:`RoleConnection`
            The role connection before the update.
        after : :class:`RoleConnection`
            The role connection after the update.
        """
        pass
