# Copyright (c) 2023-present staciax
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import LinkedRolesOAuth2
    from .http import OAuth2TokenResponse as OAuth2TokenPayload


class OAuth2Token:

    if TYPE_CHECKING:
        access_token: str
        refresh_token: str
        expires_in: int
        expires_at: datetime

    def __init__(self, client: LinkedRolesOAuth2, data: OAuth2TokenPayload) -> None:
        self._client = client
        self._update(data)

    def _update(self, data: OAuth2TokenPayload) -> None:
        self.access_token: str = data['access_token']
        self.refresh_token: str = data['refresh_token']
        self.expires_in: int = data['expires_in']
        self.expires_at: datetime = datetime.now() + timedelta(seconds=self.expires_in)

    def is_expired(self) -> bool:
        return datetime.now() >= self.expires_at

    async def refresh(self) -> None:
        data = await self._client._http.refresh_oauth2_token(self.refresh_token)
        self._update(data)
