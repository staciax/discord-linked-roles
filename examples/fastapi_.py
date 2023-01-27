import datetime
import logging
from typing import Optional

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

import _config
from linked_roles import LinkedRolesOAuth2, OAuth2Scopes, OAuth2Unauthorized, RolePlatform, User, UserNotFound

_log = logging.getLogger(__name__)

app = FastAPI(title='Linked Roles API', version='1.1.0')


class LinkedRolesClient(LinkedRolesOAuth2):
    def __init__(self):
        super().__init__(
            client_id=_config.DISCORD_CLIENT_ID,
            client_secret=_config.DISCORD_CLIENT_SECRET,
            redirect_uri=_config.DISCORD_REDIRECT_URI,
            token=_config.DISCORD_TOKEN,
            scopes=(OAuth2Scopes.role_connection_write, OAuth2Scopes.identify),
            state=_config.COOKIE_SECRET,
        )

    async def on_user_application_role_connection_update(
        self, user: User, before: RolePlatform, after: RolePlatform
    ) -> None:
        _log.info(f'User {user} updated their role connection from {before} to {after}')


client = LinkedRolesClient()


class Player(BaseModel):
    name: str = Field(..., max_length=19)
    tag: str = Field(..., max_length=5)
    matches: int = Field(..., ge=0)
    winrate: float = Field(..., ge=0, le=100)
    combat_score: int = Field(..., ge=0)
    competitive_rank: Optional[str] = Field(None)
    owner_id: int = Field(..., ge=0)

    @property
    def display_name(self) -> str:
        return self.name + '#' + self.tag


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

    # get tokens
    tokens = await client.get_oauth2_tokens(code)

    # get user
    user = await client.fetch_user(tokens=tokens)

    if user is None:
        raise UserNotFound('User not found')

    # set role platform
    platform = RolePlatform(name='VALORANT', username=str(user))

    # add metadata
    platform.add_metadata(key='matches', value=10)
    platform.add_metadata(key='winrate', value=20)
    platform.add_metadata(key='combat_score', value=30)

    # set role metadata
    await user.edit_role_metadata(platform=platform)

    return '<h1>Role metadata set successfully. Please check your Discord profile.</h1>'


@app.post('/update-role-metadata')
async def update_role_metadata(player: Player):

    # get user to make sure they are still connected
    user = client.get_user(id=player.owner_id)

    if user is None:
        raise UserNotFound(f'User with ID {player.owner_id} not found')

    # get tokens to make sure they are still authenticated
    tokens = user.get_tokens()
    if tokens is None:
        raise OAuth2Unauthorized(f'User ID {player.owner_id} is not authenticated')

    # get user role platform
    before = user.get_role_platform()

    if before is None:
        raise UserNotFound(f'User with ID {player.owner_id} has no role connection')

    # copy role platform because we don't want to edit the original
    platform = before.copy()

    platform.username = player.display_name
    if player.competitive_rank is not None:
        platform.username += f' ({player.competitive_rank})'

    # edit metadata
    platform.edit_metadata(key='matches', value=player.matches)
    platform.edit_metadata(key='winrate', value=int(player.winrate))
    platform.edit_metadata(key='combat_score', value=int(player.combat_score))

    # new metadata
    platform.add_or_edit_metadata(key='last_update', value=datetime.datetime.now())
    platform.add_or_edit_metadata(key='verified', value=True)

    # update role metadata
    await user.edit_role_metadata(platform=platform)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'status': 200,
            'message': 'Updated role metadata successfully',
            'user': player.owner_id,
            'platform': {'before': before.to_dict(), 'after': platform.to_dict()},
        },
    )


@app.post('/authenticated')
async def is_is_authenticated(discord_id: int):
    # check if user is authenticated
    user = client.get_user(discord_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content={'status': 200, 'authenticated': user is not None})
