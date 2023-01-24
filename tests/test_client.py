# Copyright (c) 2023-present staciax
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.

import pytest

from linked_roles import LinkedRolesOAuth2, OAuth2Scopes, RolePlatform

from . import _config as config


@pytest.mark.asyncio
async def test_linked_roles_client():
    client = LinkedRolesOAuth2(
        client_id=config.DISCORD_CLIENT_ID,
        client_secret=config.DISCORD_CLIENT_SECRET,
        redirect_uri=config.DISCORD_REDIRECT_URI,
        token=config.DISCORD_TOKEN,
        scopes=(OAuth2Scopes.role_connection_write, OAuth2Scopes.identify),
        state=config.COOKIE_SECRET,
    )
    assert client._http.client_id == config.DISCORD_CLIENT_ID
    assert client._http.token == config.DISCORD_TOKEN
    assert client._http.redirect_uri == config.DISCORD_REDIRECT_URI
    assert client._http.scopes == (OAuth2Scopes.role_connection_write, OAuth2Scopes.identify)
    assert client._http.state == config.COOKIE_SECRET
    assert client._http._session is None
    await client.start()
    assert client._http._session is not None
    assert client.is_closed() is False
    await client.close()
    assert client.is_closed() is True
    assert client.clear() is None
    assert client._http._session is None
