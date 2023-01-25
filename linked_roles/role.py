# Copyright (c) 2023-present staciax
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Mapping, Optional, Tuple, Type, TypeVar, Union

from .enums import AppRoleConnectionMetadataRecordType as RoleMetadataType

if TYPE_CHECKING:

    from typing_extensions import Self

    from .http import (
        AppRoleConnectionMetadataRecord as RoleMetadataRecordPayload,
        UserRoleConnection as UserRoleConnectionPayload,
    )

    MetadataDataType = Union[str, int, bool, datetime]

__all__: Tuple[str, ...] = (
    'RolePlatform',
    'RoleMetadata',
    'RoleMetadataRecord',
)

PlatformT = TypeVar('PlatformT', bound='RolePlatform')

VALID_ROLE_METADATA_KEY = r'^[A-Za-z0-9_]{0,50}$'


def validate_metadata_key(key: str) -> str:
    """Validate a metadata key."""
    match = re.match(VALID_ROLE_METADATA_KEY, key)
    if not match:
        raise ValueError(f'{key!r} must be between 1-50 and only contain letters, numbers, and underscores')

    if key.lower() != key:
        raise ValueError(f'{key!r} must be lowercase')

    return key


class RolePlatform:
    """
    Represents a platform that a role is connected to.

    Parameters
    ----------
    name : Optional[:class:`str`]
        The name of the platform.
    username : Optional[:class:`str`]
        The username of the platform.
    Attributes
    ----------
    name : :class:`str`
        The name of the platform.
    username : :class:`str`
        The username of the platform.
    """

    def __init__(self, *, name: Optional[str], username: Optional[str]):
        if name is None:
            name = ''
        if len(name) > 50:
            raise ValueError('Platform name must be less than 50 characters')
        self.name: str = name
        if username is None:
            username = ''
        if len(username) > 100:
            raise ValueError('Platform username must be less than 100 characters')
        self.username: str = username
        self._metadata: Dict[str, RoleMetadata] = {}

    def __repr__(self) -> str:
        return f'<RolePlatform name={self.name!r} username={self.username!r}>'

    def get_all_metadata(self) -> List[RoleMetadata]:
        """Get all metadata for this platform.
        Returns
        -------
        List[:class:`RoleMetadata`]
            A list of metadata.
        """
        return list(self._metadata.values())

    def get_metadata(self, key: str) -> Optional[RoleMetadata]:
        """Get a metadata value for this platform.
        Parameters
        ----------
        key : :class:`str`
            The key of the metadata.
        Returns
        -------
        Optional[:class:`RoleMetadata`]
            The metadata value.
        """
        return self._metadata.get(key)

    def add_metadata(self, key: str, value: MetadataDataType) -> Self:
        """
        Add a metadata value to this platform.
        Parameters
        ----------
        key : :class:`str`
            The key of the metadata.
        value : Union[:class:`str`, :class:`int`, :class:`bool`, :class:`datetime.datetime`]
            The value of the metadata.
        Returns
        -------
        :class:`RolePlatform`
            The platform.
        Raises
        ------
        ValueError
            The key is already in use.
        """
        metadata = self.get_metadata(key)
        if metadata is not None:
            raise ValueError(f'{key!r} already exists')
        self._metadata[key] = RoleMetadata(key=key, value=value)
        return self

    def edit_metadata(self, key: str, value: MetadataDataType) -> Self:
        """
        Edit a metadata value for this platform.
        Parameters
        ----------
        key : :class:`str`
            The key of the metadata.
        value : Union[:class:`str`, :class:`int`, :class:`bool`, :class:`datetime.datetime`]
            The value of the metadata.
        Returns
        -------
        :class:`RolePlatform`
            The platform.
        Raises
        ------
        ValueError
            The key does not exist.
        """
        metadata = self.get_metadata(key)
        if metadata is None:
            raise ValueError(f'{key!r} does not exist')
        metadata.value = value
        return self

    def to_dict(self) -> Mapping[str, Any]:
        """Convert the platform to a dictionary.
        Returns
        -------
        Dict[:class:`str`, Any]
            The platform as a dictionary.
        """
        payload = {
            'platform_name': self.name,
            'platform_username': self.username,
            'metadata': {},
        }
        if self._metadata:
            meta_payload = {}
            for key, metadata in self._metadata.items():
                if isinstance(metadata.value, datetime):
                    meta_payload[key] = metadata.value.isoformat()
                elif isinstance(metadata.value, bool):
                    meta_payload[key] = int(metadata.value)
                else:
                    meta_payload[key] = metadata.value
            payload['metadata'] = meta_payload
        return payload

    @classmethod
    def from_dict(cls: Type[Self], data: UserRoleConnectionPayload) -> Self:
        """
        Create a platform from a dictionary.
        Parameters
        ----------
        data: UserRoleConnectionPayload
            The dictionary to create the platform from.
        Returns
        -------
        :class:`RolePlatform`
            The platform.
        """
        platform = cls(
            name=data['platform_name'],
            username=data['platform_username'],
        )
        metadata = data.get('metadata')
        if metadata is not None:
            for key, value in metadata.items():
                platform.add_metadata(key=key, value=value)
        return platform


class RoleMetadata:
    """
    Represents a metadata value for a role.
    Parameters
    ----------
    key : :class:`str`
        The key of the metadata.
    value : Union[:class:`str`, :class:`int`, :class:`bool`, :class:`datetime.datetime`]
        The value of the metadata.
    """

    def __init__(self, key: str, value: MetadataDataType):
        self.key: str = validate_metadata_key(key)
        self.value: MetadataDataType = value

    def __repr__(self) -> str:
        return f'<RoleMetadata key={self.key!r} value={self.value!r}>'

    def to_dict(self) -> Dict[str, Any]:
        """Convert the metadata to a dictionary.
        Returns
        -------
        Dict[:class:`str`, Any]
            The metadata as a dictionary.
        """
        return {
            'key': self.key,
            'value': self.value,
        }


class RoleMetadataRecord(Generic[PlatformT]):
    """
    Represents a metadata record for a role.
    Parameters
    ----------
    key : :class:`str`
        The key of the metadata.
    name : :class:`str`
        The name of the metadata.
    type : Union[:class:`RoleMetadataType`, :class:`int`]
        The type of the metadata.
    description : :class:`str`
        The description of the metadata.
    name_localizations : Optional[Dict[:class:`str`, :class:`str`]]
        The name localizations of the metadata.
    description_localizations : Optional[Dict[:class:`str`, :class:`str`]]
        The description localizations of the metadata.
    """

    def __init__(
        self,
        *,
        key: str,
        name: str,
        type: Union[RoleMetadataType, int],
        description: Optional[str] = None,
        name_localizations: Optional[Dict[str, str]] = None,
        description_localizations: Optional[Dict[str, str]] = None,
    ) -> None:
        self.key: str = validate_metadata_key(key)
        if len(name) > 100:
            raise ValueError('Metadata name must be 100 characters or less')
        self.name: str = name
        if description is None:
            description = '...'
        if len(description) > 200:
            raise ValueError('Metadata description must be 200 characters or less')
        self.description: str = description
        if not isinstance(type, RoleMetadataType):
            try:
                type = RoleMetadataType(type)
            except ValueError:
                raise ValueError(f'{type!r} is not a valid RoleMetadataType')
        self._type: RoleMetadataType = type
        self.name_localizations = name_localizations
        self.description_localizations: Optional[Dict[str, Any]] = description_localizations
        self._parent: Optional[PlatformT] = None  # or self._platform?

    def __repr__(self) -> str:
        return f'<RoleMetadata key={self.key!r} name={self.name!r} type={self._type!r}>'

    def __eq__(self, other) -> bool:
        return isinstance(other, RoleMetadataRecord) and self.key == other.key

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    @property
    def parent(self) -> Optional[PlatformT]:
        """Optional[:class:`RolePlatform`]: The parent platform of the metadata record."""
        return self._parent

    @property
    def data_type(self) -> Optional[Type[Union[int, datetime, bool]]]:
        """Optional[Type[Union[:class:`int`, :class:`datetime.datetime`, :class:`bool`]]]: The data type of the metadata record."""
        return self._type.data_type

    def to_dict(self) -> Dict[str, Any]:
        """Convert the metadata record to a dictionary.
        Returns
        -------
        Dict[:class:`str`, Any]
            The metadata record as a dictionary.
        """
        payload = {
            'key': self.key,
            'name': self.name,
            'description': self.description,
            'type': self._type.value,
        }
        if self.name_localizations is not None:
            payload['name_localizations'] = self.name_localizations
        if self.description_localizations is not None:
            payload['description_localizations'] = self.description_localizations
        return payload

    @classmethod
    def from_dict(cls, data: RoleMetadataRecordPayload) -> Self:
        """
        Create a metadata record from a dictionary.
        Parameters
        ----------
        data: RoleMetadataRecordPayload
            The dictionary to create the metadata record from.
        Returns
        -------
        :class:`RoleMetadataRecord`
            The metadata record.
        """
        return cls(
            key=data['key'],
            name=data['name'],
            description=data['description'],
            type=RoleMetadataType(data['type']),
            name_localizations=data.get('name_localizations'),
            description_localizations=data.get('description_localizations'),
        )
