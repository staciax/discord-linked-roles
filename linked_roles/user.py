# Copyright (c) 2023-present staciax
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from .errors import RoleLinkedNotFound
from .role import RoleConnection

if TYPE_CHECKING:
    from .client import LinkedRolesOAuth2
    from .http import User as UserPayload
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
    tokens : Optional[:class:`OAuth2Token`]
        The tokens of the user.
    """

    def __init__(self, client: LinkedRolesOAuth2, data: UserPayload, *, tokens: Optional[OAuth2Token] = None):
        super().__init__(data)
        self.client = client
        self._tokens: Optional[OAuth2Token] = tokens
        self._role_connection: Optional[RoleConnection] = None
        self.__before_role_connectiion_update__: Optional[RoleConnection] = None

    def _update(self, data: UserPayload, tokens: Optional[OAuth2Token] = None) -> None:
        super()._update(data)
        if tokens is not None:
            self._tokens = tokens

    def get_role_connection(self) -> Optional[RoleConnection]:
        """ " Returns the role connection of the user.
        Returns
        -------
        Optional[:class:`RoleConnection`]
            The role connection of the user.
        """
        return self._role_connection

    async def fetch_role_connection(self) -> Optional[RoleConnection]:
        """ " Fetches the role connection of the user.
        Returns
        -------
        Optional[:class:`RoleConnection`]
            The role connection of the user.
        Raises
        ------
        :class:`RoleLinkedNotFound`
            The user is not linked role or user not oauth2.
        """
        tokens = self.get_tokens()
        if tokens is not None:
            data = await self.client._http.get_user_application_role_connection(tokens.access_token)
            if data is None:
                raise RoleLinkedNotFound("The user is not linked role or user not oauth2.")
            self._role_connection = RoleConnection.from_dict(data)
        return self._role_connection

    async def get_or_fetch_role_connection(self) -> Optional[RoleConnection]:
        """ " Gets or fetches the role connection of the user.
        Returns
        -------
        Optional[:class:`RoleConnection`]
            The role connection of the user.
        """
        if self._role_connection is None:
            try:
                await self.fetch_role_connection()
            except RoleLinkedNotFound:
                return None
        return self._role_connection

    async def refresh_role_connection(self) -> Optional[RoleConnection]:
        """ " Refreshes the role connection of the user.
        Returns
        -------
        Optional[:class:`RoleConnection`]
            The role connection of the user.
        """
        tokens = self.get_tokens()
        if tokens is not None:
            data = await self.client._http.get_user_application_role_connection(tokens.access_token)
            self._role_connection = RoleConnection.from_dict(data)
        return self._role_connection

    def get_tokens(self) -> Optional[OAuth2Token]:
        """ " Returns the tokens of the user.
        Returns
        -------
        Optional[:class:`OAuth2Token`]
            The tokens of the user.
        """
        if self._tokens is not None:
            if self._tokens.is_expired():
                self.client.loop.create_task(self._tokens.refresh())
        return self._tokens

    def set_tokens(self, value: OAuth2Token) -> None:
        """ " Sets the tokens of the user.
        Parameters
        ----------
        value : :class:`OAuth2Token`
            The tokens of the user.
        """
        self._tokens = value

    async def edit_role_connection(self, role: RoleConnection) -> Optional[RoleConnection]:
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

        if self.__before_role_connectiion_update__ is None and self._role_connection is not None:
            self.__before_role_connectiion_update__ = self._role_connection.copy()

        if self.client.is_role_metadata_fetched():
            for metadata in role.get_all_metadata():

                # verify metadata
                get_metadata = self.client.get_role_metadata(metadata.key)

                if get_metadata is None:
                    raise ValueError(f'Role metadata {metadata.key!r} is not found')

                if get_metadata.data_type is not None:
                    if not isinstance(metadata.value, get_metadata.data_type):
                        raise TypeError(f'Role metadata {metadata.key!r} value must be {get_metadata.data_type!r}')

        new_role = await self.client.edit_user_role_connection(self, role)
        if new_role is not None:
            if self._role_connection is not None:
                self._role_connection = new_role
        return self.get_role_connection()
