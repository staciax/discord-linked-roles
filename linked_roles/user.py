# Copyright (c) 2023-present staciax
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from .role import RoleConnection

if TYPE_CHECKING:
    from .client import LinkedRolesOAuth2
    from .http import OAuth2TokenResponse as OAuth2TokenPayload, User as UserPayload
    from .oauth2 import OAuth2Token

    Snowflake = Union[str, int]


class BaseUser:
    """
    Represents a base user.

    Parameters
    ----------
    data : :class:`UserPayload`
        The data of the user.
    Attributes
    id : :class:`Snowflake`
        The ID of the user.
    username : :class:`str`
        The username of the user.
    discriminator : :class:`str`
        The discriminator of the user.
    _avatar : Optional[:class:`str`]
        The avatar of the user."""

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
        self.bot: bool = data.get('bot') or False
        self.system: bool = data.get('system') or False
        self.accent_color: Optional[int] = data.get('accent_color')

    def __repr__(self) -> str:
        return f'<User id={self.id!r} username={self.username!r} discriminator={self.discriminator!r}>'

    def __str__(self) -> str:
        return f'{self.username}#{self.discriminator}'

    @property
    def avatar_url(self) -> Optional[str]:
        """:class:`Optional[:class:`str`] The avatar URL of the user."""
        if self._avatar is None:
            return None
        return f'https://cdn.discordapp.com/avatars/{self.id}/{self._avatar}.png?size=1024'

    @property
    def banner_url(self) -> Optional[str]:
        """:class:`Optional[:class:`str`] The banner URL of the user."""
        if self._banner is None:
            return None
        animated = self._banner.startswith('a_')
        format = 'gif' if animated else 'png'
        return f'https://cdn.discordapp.com/banners/{self.id}/{self._banner}.{format}?size=1024'


class User(BaseUser):
    """
    Represents a user.

    Parameters
    ----------
    client : :class:`LinkedRolesOAuth2`
        The client of the user.
    data : :class:`UserPayload`
        The data of the user.
    token : Optional[:class:`OAuth2Token`]
        The token of the user.
    """

    def __init__(self, client: LinkedRolesOAuth2, data: UserPayload, token: OAuth2Token):
        super().__init__(data)
        self._client = client
        self._token: OAuth2Token = token
        self._role_connectiion: Optional[RoleConnection] = None

    def _update(self, data: UserPayload) -> None:
        super()._update(data)

    def _update_token(self, data: OAuth2TokenPayload) -> None:
        self._token._update(data)

    def get_token(self) -> OAuth2Token:
        """Gets the token of the user.
        Returns
        -------
        :class:`OAuth2Token`
            The token of the user.
        """
        return self._token

    async def fetch_role_connection(self) -> Optional[RoleConnection]:
        """Fetches the role connection of the user.
        Returns
        -------
        Optional[:class:`RoleConnection`]
            The role connection of the user.
        Raises
        ------
        :class:`RoleLinkedNotFound`
            The user is not linked role or user not oauth2.
        """
        await self._refresh_token()
        data = await self._client._http.get_user_application_role_connection(self._token.access_token)
        if data:
            self._role_connectiion = RoleConnection.from_dict(data)
        return self._role_connectiion

    async def _refresh_token(self, *, force: bool = False) -> None:
        """Refreshes the token of the user."""
        if self._token.is_expired() or force:
            await self._token.refresh()

    async def edit_role_connection(self, role: RoleConnection) -> RoleConnection:
        """Edits the role metadata of the user.
        Parameters
        ----------
        role : :class:`RoleConnection`
            The role connection of the user.
        Returns
        -------
        Optional[:class:`RoleConnection`]
            The role connection of the user.
        Raises
        ------
        ValueError
            The role metadata is not found.
        TypeError
            The role metadata value must be the same type.
        """

        if self._client.is_role_metadata_fetched():
            for metadata in role.get_all_metadata():

                # verify metadata
                get_metadata = self._client.get_role_metadata(metadata.key)

                if get_metadata is None:
                    raise ValueError(f'Role metadata {metadata.key!r} is not found')

                if get_metadata.data_type is not None:
                    if not isinstance(metadata.value, get_metadata.data_type):
                        raise TypeError(f'Role metadata {metadata.key!r} value must be {get_metadata.data_type!r}')

        # refresh token
        await self._refresh_token()

        data = await self._client._http.put_user_application_role_connection(self._token.access_token, role.to_dict())
        after = RoleConnection.from_dict(data)
        self._client.loop.create_task(
            self._client.on_user_application_role_connection_update(self, self._role_connectiion or after, after)
        )
        self._role_connectiion = after
        return after
