# Copyright (c) 2023-present staciax
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from .client import LinkedRolesOAuth2
    from .http import User as UserPayload
    from .oauth2 import OAuth2Token
    from .role import RolePlatform

    Snowflake = Union[str, int]


class BaseUser:
    if TYPE_CHECKING:
        id: Snowflake
        username: str
        discriminator: str
        _avatar: Optional[str]
        _banner: Optional[str]
        bot: bool
        system: bool
        accent_color: Optional[int]

    def __init__(self, data: UserPayload):
        self._update(data)

    def _update(self, data: UserPayload) -> None:
        self.id: Snowflake = data.get('id')
        self.username: str = data.get('username')
        self.discriminator: str = data.get('discriminator')
        self._avatar: Optional[str] = data.get('avatar')
        self._banner: Optional[str] = data.get('banner')
        self.bot: bool = data.get('bot', False)
        self.system: bool = data.get('system', False)
        self.accent_color: Optional[int] = data.get('accent_color')

    def __repr__(self) -> str:
        return f'<User id={self.id!r} username={self.username!r} discriminator={self.discriminator!r}>'

    def __str__(self) -> str:
        return f'{self.username}#{self.discriminator}'


class User(BaseUser):
    def __init__(self, client: LinkedRolesOAuth2, data: UserPayload, *, tokens: Optional[OAuth2Token] = None):
        super().__init__(data)
        self.client = client
        self._role_platform: Optional[RolePlatform] = None
        self._tokens: Optional[OAuth2Token] = tokens
        self.__orginal_role_platform__: Optional[RolePlatform] = None

    def _update(self, data: UserPayload, tokens: Optional[OAuth2Token] = None) -> None:
        super()._update(data)
        if tokens is not None:
            self._tokens = tokens

    def get_role_platform(self) -> Optional[RolePlatform]:
        return self._role_platform

    def get_tokens(self) -> Optional[OAuth2Token]:
        return self._tokens

    def set_tokens(self, value: OAuth2Token) -> None:
        self._tokens = value

    @property
    def role_platform(self) -> Optional[RolePlatform]:
        return self._role_platform

    @role_platform.setter
    def role_platform(self, value: RolePlatform) -> None:
        self.__orginal_role_platform__ = self._role_platform = value

    async def edit_role_metadata(self, platform: Optional[RolePlatform] = None) -> RolePlatform:
        if platform is None and self._role_platform is None:
            platform = RolePlatform(name='Linked Roles', username=self.username)

        self.role_platform = platform = platform or self._role_platform

        if self.client.is_role_metadata_fetched():
            for metadata in platform.get_all_metadata():

                # verify metadata
                get_metadata = self.client.get_role_metadata(metadata.key)

                if get_metadata is None:
                    raise ValueError(f'Role metadata {metadata.key!r} is not found')

                if not isinstance(metadata.value, get_metadata.data_type):
                    raise TypeError(f'Role metadata {metadata.key!r} value must be {get_metadata.data_type!r}')

        return await self.client.edit_user_application_role_connection(self, platform)
