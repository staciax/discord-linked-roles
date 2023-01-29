# Copyright (c) 2023-present staciax
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Mapping, Optional, Tuple, Type, TypeVar, Union

from .enums import AppRoleConnectionMetadataRecordType as RoleMetadataType

if TYPE_CHECKING:
    from typing_extensions import Self

    from .http import AppRoleConnectionMetadataRecord as RoleMetadataRecordPayload

    MetadataDataType = Union[str, int, bool, datetime]

__all__: Tuple[str, ...] = (
    'RoleConnection',
    'RoleMetadata',
    'RoleMetadataRecord',
)

RoleConnectionT = TypeVar('RoleConnectionT', bound='RoleConnection')

VALID_ROLE_METADATA_KEY = r'^[A-Za-z0-9_]{0,50}$'


def validate_metadata_key(key: str) -> str:
    """Validate a metadata key."""
    match = re.match(VALID_ROLE_METADATA_KEY, key)
    if not match:
        raise ValueError(f'{key!r} must be between 1-50 and only contain letters, numbers, and underscores')

    if key.lower() != key:
        raise ValueError(f'{key!r} must be lowercase')

    return key


class RoleConnection:
    """
    Represents a role connection.

    Parameters
    ----------
    platform_name : Optional[:class:`str`]
        The name of the platform.
    platform_username : Optional[:class:`str`]
        The username of the platform.
    Attributes
    ----------
    platform_name : :class:`str`
        The name of the platform.
    platform_username : :class:`str`
        The username of the platform.
    """

    def __init__(self, *, platform_name: Optional[str] = None, platform_username: Optional[str] = None):
        if platform_name is None:
            platform_name = ''
        if len(platform_name) > 50:
            raise ValueError('platform name must be less than 50 characters')
        self.platform_name: str = platform_name
        if platform_username is None:
            platform_username = ''
        if len(platform_username) > 100:
            raise ValueError('platform username must be less than 100 characters')
        self.platform_username: str = platform_username
        self._metadata: Dict[str, RoleMetadata] = {}

    def __repr__(self) -> str:
        return f'<RoleConnection platform_name={self.platform_name!r} platform_username={self.platform_username!r}>'

    def get_all_metadata(self) -> List[RoleMetadata]:
        """Get all metadata for this role connection.
        Returns
        -------
        List[:class:`RoleMetadata`]
            A list of metadata.
        """
        return list(self._metadata.values())

    def get_metadata(self, key: str) -> Optional[RoleMetadata]:
        """Get a metadata value for this role connection.
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
        Add a metadata value to this role connection.
        Parameters
        ----------
        key : :class:`str`
            The key of the metadata.
        value : Union[:class:`str`, :class:`int`, :class:`bool`, :class:`datetime.datetime`]
            The value of the metadata.
        Returns
        -------
        :class:`RoleConnection`
            The role connection.
        Raises
        ------
        ValueError
            You can only have 5 metadata values per platform role connection or the key already exists.
        """
        if len(self._metadata) >= 5:
            raise ValueError('You can only have 5 metadata values per platform')
        metadata = self.get_metadata(key)
        if metadata is not None:
            raise ValueError(f'{key!r} already exists')
        self._metadata[key] = RoleMetadata(key=key, value=value)
        return self

    def edit_metadata(self, key: str, value: MetadataDataType) -> Self:
        """
        Edit a metadata value for this role connection.
        Parameters
        ----------
        key : :class:`str`
            The key of the metadata.
        value : Union[:class:`str`, :class:`int`, :class:`bool`, :class:`datetime.datetime`]
            The value of the metadata.
        Returns
        -------
        :class:`RoleConnection`
            The role connection.
        Raises
        ------
        ValueError
            The key does not exist.
        """
        metadata = self.get_metadata(key)
        if metadata is not None:
            metadata.value = value
        return self

    def add_or_edit_metadata(self, key: str, value: MetadataDataType) -> Self:
        """
        Add or edit a metadata value for this role connection.
        Parameters
        ----------
        key : :class:`str`
            The key of the metadata.
        value : Union[:class:`str`, :class:`int`, :class:`bool`, :class:`datetime.datetime`]
            The value of the metadata.
        Returns
        -------
        :class:`RoleConnection`
            The role connection.
        """
        metadata = self.get_metadata(key)
        if metadata is None:
            self.add_metadata(key, value)
        else:
            self.edit_metadata(key, value)
        return self

    def remove_metadata(self, key: str) -> Self:
        """
        Remove a metadata value from this role connection.
        Parameters
        ----------
        key : :class:`str`
            The key of the metadata.
        Returns
        -------
        :class:`RoleConnection`
            The role connection.
        Raises
        ------
        ValueError
            The key does not exist.
        """
        try:
            del self._metadata[key]
        except KeyError:
            pass
        return self

    def clear_metadata(self) -> Self:
        """Clear all metadata from this role connection.
        Returns
        -------
        :class:`RoleConnection`
            The role connection.
        """

        try:
            self._metadata.clear()
        except AttributeError:
            self._metadata = {}

        return self

    def copy(self) -> Self:
        """Copy the role connection.
        Returns
        -------
        :class:`RoleConnection`
            The copied role connection.
        """
        return self.__class__.from_dict(self.to_dict())

    def to_dict(self) -> Mapping[str, Any]:
        """Convert the role connection to a dictionary.
        Returns
        -------
        Dict[:class:`str`, Any]
            The role connection as a dictionary.
        """
        payload = {
            'platform_name': self.platform_name,
            'platform_username': self.platform_username,
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
    def from_dict(cls: Type[Self], data: Mapping[str, Any]) -> Self:
        """
        Create a role connection from a dictionary.
        Parameters
        ----------
        data: Mapping[:class:`str`, Any]
            The dictionary to create the role connection from.
        Returns
        -------
        :class:`RoleConnection`
            The role connection.
        """
        self = cls.__new__(cls)
        self.platform_name = data.get('platform_name', '')
        self.platform_username = data.get('platform_username', '')
        self._metadata = {}
        metadata = data.get('metadata')
        if metadata is not None:

            def is_int(s: str) -> bool:
                try:
                    int(s)
                    return True
                except ValueError:
                    return False

            for key, value in metadata.items():
                # TODO: check value type
                if isinstance(value, str):
                    if is_int(value):
                        value = int(value)
                    # elif value.count('-') == 2:
                    #     value = datetime.fromisoformat(value)
                self.add_metadata(key=key, value=value)
        return self


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


class RoleMetadataRecord(Generic[RoleConnectionT]):
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
        self._parent: Optional[RoleConnectionT] = None  # or self._platform?

    def __repr__(self) -> str:
        return f'<RoleMetadata key={self.key!r} name={self.name!r} type={self._type!r}>'

    def __eq__(self, other) -> bool:
        return isinstance(other, RoleMetadataRecord) and self.key == other.key

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    @property
    def parent(self) -> Optional[RoleConnectionT]:
        """Optional[:class:`RoleConnection`]: The parent role connection of the metadata record."""
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
