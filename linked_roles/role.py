# Copyright (c) 2023-present staciax
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar, Union

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
    match = re.match(VALID_ROLE_METADATA_KEY, key)
    if not match:
        raise ValueError(f'{key!r} must be between 1-50 and only contain letters, numbers, and underscores')

    if key.lower() != key:
        raise ValueError(f'{key!r} must be lowercase')

    return key


class RolePlatform:
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
        return list(self._metadata.values())

    def get_metadata(self, key: str) -> Optional[RoleMetadata]:
        return self._metadata.get(key)

    def add_metadata(self, key: str, value: MetadataDataType) -> Self:
        metadata = self.get_metadata(key)
        if metadata is not None:
            raise ValueError(f'{key!r} already exists')
        self._metadata[key] = RoleMetadata(key=key, value=value)
        return self

    def edit_metadata(self, key: str, value: MetadataDataType) -> Self:
        metadata = self.get_metadata(key)
        if metadata is None:
            raise ValueError(f'{key!r} does not exist')
        metadata.value = value
        return self

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            'platform_name': self.name,
            'platform_username': self.username,
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
            payload['metadata'] = meta_payload  # type: ignore
        return payload

    @classmethod
    def from_dict(cls: Type[Self], data: UserRoleConnectionPayload) -> Self:
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
    def __init__(self, key: str, value: MetadataDataType):
        self.key: str = validate_metadata_key(key)
        self.value: MetadataDataType = value

    def __repr__(self) -> str:
        return f'<RoleMetadata key={self.key!r} value={self.value!r}>'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'key': self.key,
            'value': self.value,
        }


class RoleMetadataRecord(Generic[PlatformT]):
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
        return self._parent

    @property
    def data_type(self) -> Optional[Type[Union[int, datetime, bool]]]:
        return self._type.data_type

    def to_dict(self) -> Dict[str, Any]:
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
        return cls(
            key=data['key'],
            name=data['name'],
            description=data['description'],
            type=RoleMetadataType(data['type']),
            name_localizations=data.get('name_localizations'),
            description_localizations=data.get('description_localizations'),
        )
