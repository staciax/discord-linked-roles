import datetime
import logging
from typing import Optional

import config
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from linked_roles import LinkedRolesOAuth2, OAuth2Scopes, OAuth2Unauthorized, RoleConnection, User, UserNotFound

_log = logging.getLogger(__name__)

app = FastAPI(title='Linked Roles API', version='1.1.0')


class LinkedRolesClient(LinkedRolesOAuth2):
    def __init__(self):
        super().__init__(
            client_id=config.DISCORD_CLIENT_ID,
            client_secret=config.DISCORD_CLIENT_SECRET,
            redirect_uri=config.DISCORD_REDIRECT_URI,
            token=config.DISCORD_TOKEN,
            scopes=(OAuth2Scopes.role_connection_write, OAuth2Scopes.identify),
            state=config.COOKIE_SECRET,
        )

    async def on_user_application_role_connection_update(
        self, user: User, before: RoleConnection, after: RoleConnection
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

    # set role connection
    role = RoleConnection(platform_name='VALORANT', platform_username=str(user))

    # add metadata
    role.add_metadata(key='matches', value=10)
    role.add_metadata(key='winrate', value=20)
    role.add_metadata(key='combat_score', value=30)

    # set role metadata
    await user.edit_role_connection(role)

    return '<h1>Role metadata set successfully. Please check your Discord profile.</h1>'


@app.put('/update-role-metadata')
async def update_role_metadata(player: Player):

    # get user to make sure they are still connected
    user = client.get_user(id=player.owner_id)

    if user is None:
        raise UserNotFound(f'User with ID {player.owner_id} not found')

    # get tokens to make sure they are still authenticated
    tokens = user.get_tokens()
    if tokens is None:
        raise OAuth2Unauthorized(f'User ID {player.owner_id} is not authenticated')

    # get user role connection
    before = await user.get_or_fetch_role_connection()

    if before is None:
        raise UserNotFound(f'User with ID {player.owner_id} has no role connection')

    # copy role connection to make changes
    role = before.copy()

    role.platform_username = player.display_name
    if player.competitive_rank is not None:
        role.platform_username += f' ({player.competitive_rank})'

    # edit metadata
    role.edit_metadata(key='matches', value=player.matches)
    role.edit_metadata(key='winrate', value=int(player.winrate))
    role.edit_metadata(key='combat_score', value=int(player.combat_score))

    # new metadata
    role.add_or_edit_metadata(key='last_update', value=datetime.datetime.now())
    role.add_or_edit_metadata(key='verified', value=True)

    # update role connection
    await user.edit_role_connection(role)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'status': 200,
            'message': 'Updated role metadata successfully',
            'user': player.owner_id,
            'connection': {'before': before.to_dict(), 'after': role.to_dict()},
        },
    )


@app.post('/authenticated')
async def is_is_authenticated(discord_id: int):
    # check if user is authenticated
    user = client.get_user(discord_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content={'status': 200, 'authenticated': user is not None})
