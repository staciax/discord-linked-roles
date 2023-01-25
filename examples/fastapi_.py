# Copyright (c) 2023-present staciax
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.

import datetime
import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

import _config
from linked_roles import (
    LinkedRolesOAuth2,
    OAuth2Scopes,
    OAuth2Unauthorized,
    RateLimited,
    RolePlatform,
    Unauthorized,
    UserNotFound,
)

_log = logging.getLogger(__name__)

app = FastAPI(title='Linked Roles API', version='0.1.0')

client = LinkedRolesOAuth2(
    client_id=_config.DISCORD_CLIENT_ID,
    client_secret=_config.DISCORD_CLIENT_SECRET,
    redirect_uri=_config.DISCORD_REDIRECT_URI,
    # token=config.DISCORD_TOKEN,  # Optinal for Resgister
    scopes=(OAuth2Scopes.role_connection_write, OAuth2Scopes.identify),
    state=_config.COOKIE_SECRET,
)


@app.on_event('startup')
async def startup():
    await client.start()
    _log.info('Startup complete')


@app.on_event('shutdown')
async def shutdown():
    await client.close()
    _log.info('Shutdown complete')


@app.get('/linked-role', status_code=status.HTTP_302_FOUND)
async def linked_roles():
    url = client.get_oauth_url()
    return RedirectResponse(url=url)


@app.get('/verified-role')
async def verified_role(code: str):

    tokens = await client.get_oauth2_tokens(code)
    user = await client.fetch_user(tokens=tokens)

    if user is None:
        raise UserNotFound('User not found')

    platform = RolePlatform(name='VALORANT', username='STACIA#1234')
    platform.add_metadata(key='matches', value=100)
    platform.add_metadata(key='winrate', value=50)
    platform.add_metadata(key='combat_score', value=10)
    platform.add_metadata(key='last_update', value=datetime.datetime.now())
    platform.add_metadata(key='verified', value=True)

    await user.edit_role_metadata(platform=platform)

    return 'Verified role successfully'


@app.post('/update-role-metadata')
async def update_role_metadata(user_id: str):

    user = client.get_user(id=user_id)

    if user is None:
        raise UserNotFound(f'User with ID {user_id} not found')

    tokens = user.get_tokens()
    if tokens is None:
        raise OAuth2Unauthorized('User is not connected to Linked Roles')

    if tokens.is_expired():
        await tokens.refresh()

    platform = user.get_role_platform()
    if platform is None:
        platform = RolePlatform(name='VALORANT', username=user.username)
    platform.edit_metadata(key='matches', value=5000)
    platform.edit_metadata(key='winrate', value=5000)
    platform.edit_metadata(key='combat_score', value=100000)
    platform.edit_metadata(key='last_update', value=datetime.datetime.now())
    platform.edit_metadata(key='verified', value=True)

    await user.edit_role_metadata(platform=platform)


@app.exception_handler(UserNotFound)
async def unauthorized_exception_handler(r: Request, e: Unauthorized):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={'error': 'Unauthorized', 'message': e.message},
    )


@app.exception_handler(UserNotFound)
async def not_found_exception_handler(r: Request, e: UserNotFound):
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={'error': 'Not found', 'message': e.message})


@app.exception_handler(RateLimited)
async def rate_limited_exception_handler(r: Request, e: RateLimited):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={'error': 'Rate limited', 'retry_after': e.retry_after, 'message': e.message},
    )
