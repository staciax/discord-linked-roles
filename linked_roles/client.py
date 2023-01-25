# Copyright (c) 2023-present staciax
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, Union

import aiohttp

from .http import HTTPClient
from .oauth2 import OAuth2Token
from .role import RoleMetadataRecord, RolePlatform
from .user import User

__all__: Tuple[str, ...] = ('LinkedRolesOAuth2',)

_log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from datetime import datetime
    from types import TracebackType

    from typing_extensions import Self

    RoleMetadataRecordType = Union[int, bool, datetime]


class LinkedRolesOAuth2:
    def __init__(
        self,
        client_id: int,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        token: Optional[str] = None,
        scopes=('role_connections.write', 'identify'),
        state: Optional[str] = None,
        proxy=None,
        proxy_auth: aiohttp.BasicAuth = None,
    ) -> None:
        self.application_id = client_id
        self._http = HTTPClient(
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
        self._users: Dict[str, User] = {}
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
        await self._http.start()
        if self._http.token is not None:
            role_connections_records = await self._http.get_application_role_connection_metadata_records()
            for record in role_connections_records:
                role_metadata = RoleMetadataRecord.from_dict(record)
                self._role_metadata[role_metadata.key] = role_metadata
            self._role_metadat_is_fetched = True

    async def close(self) -> None:
        if self._is_closed:
            return
        self._is_closed = True
        await self._http.close()

    def clear(self) -> None:
        self._role_metadata.clear()
        self._users.clear()
        self._role_metadat_is_fetched = False
        self._http.clear()

    def is_closed(self) -> bool:
        return self._is_closed

    def is_role_metadata_fetched(self) -> bool:
        return self._role_metadat_is_fetched

    def get_oauth_url(self) -> str:
        return self._http.get_oauth_url()

    async def get_oauth2_tokens(self, code: str) -> OAuth2Token:
        data = await self._http.get_oauth2_tokens(code)
        return OAuth2Token(self, data)

    async def register_role_metadata(
        self, records: List[RoleMetadataRecord], force: bool = False
    ) -> List[RoleMetadataRecord]:
        payload = []
        for record in records:
            if record.key not in self._role_metadata and not force:
                raise ValueError(f'Role metadata with key {record.key} already exists')
            payload.append(record.to_dict())
            self._role_metadata[record.key] = record
        data = await self._http.put_application_role_connection_metadata(payload)
        return [RoleMetadataRecord.from_dict(record) for record in data]

    def get_role_metadata(self, key: str) -> Optional[RoleMetadataRecord]:
        return self._role_metadata.get(key)

    async def fetch_user(self, tokens: OAuth2Token) -> User:
        data = await self._http.get_user(tokens.access_token)
        if data is None:
            return None
        user = User(self, data, tokens=tokens)
        self._users[user.id] = user
        return user

    def get_user(self, id: Union[str, int]) -> Optional[User]:
        return self._users.get(str(id))

    async def edit_user_application_role_connection(self, user: User, platform: RolePlatform) -> None:
        try:
            tokens = user.get_tokens()
            after = await self._http.put_user_application_role_connection(tokens.access_token, platform.to_dict())
        except Exception as e:
            _log.error(f'Error while updating user application role connection: {e}')
        else:
            after_platform = RolePlatform.from_dict(after)
            try:
                await self.on_user_application_role_connection_update(
                    user=user, before=user.__orginal_role_platform__ or after_platform, after=after_platform
                )
            except Exception as e:
                _log.error(f'event on_user_application_role_connection_update raised an exception: {e}')
            user.__orginal_role_platform__ = after_platform
            return after_platform

    async def on_user_application_role_connection_update(
        self,
        user: User,
        before: RolePlatform,
        after: RolePlatform,
    ) -> None:
        pass
