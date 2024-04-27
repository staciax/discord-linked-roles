import datetime
import logging
from typing import Optional

import config
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from linked_roles import LinkedRolesOAuth2, OAuth2Scopes, RoleConnection, User

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
    verified: bool = Field(False)
    owner_id: int = Field(..., ge=0)

    @property
    def display_name(self) -> str:
        return self.name + '#' + self.tag


class UserNotFound(HTTPException):
    """Exception that's thrown when the user is not found."""

    def __init__(self, user_id: Optional[int] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'User {user_id} not found' if user_id else 'User not found',
        )
        self.user_id = user_id


class RoleConnectionNotFound(HTTPException):
    """Exception that's thrown when the role connection is not found."""

    def __init__(self, user_id: int) -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=f'Role connection for user {user_id} not found')
        self.user_id = user_id


@app.on_event('startup')
async def startup():
    await client.start()
    _log.info('Startup complete')


@app.on_event('shutdown')
async def shutdown():
    await client.close()
    _log.info('Shutdown complete')


@app.get('/linked-role')
async def linked_roles():
    url = client.get_oauth_url()
    return RedirectResponse(url=url)


@app.get('/verified-role')
async def verified_role(code: str):
    # get token
    token = await client.get_access_token(code)

    # get user
    user = await client.fetch_user(token)

    if user is None:
        raise UserNotFound()

    role = await user.fetch_role_connection()
    if role is None:
        # set default role metadata
        role = RoleConnection(platform_name='VALORANT', platform_username=str(user))

        # add metadata
        role.add_metadata(key='matches', value=0)
        role.add_metadata(key='winrate', value=0)
        role.add_metadata(key='combat_score', value=0)
        role.add_metadata(key='last_update', value=datetime.datetime.utcnow())

        # set role metadata
        await user.edit_role_connection(role)

    return 'Role metadata set successfully. Please check your Discord profile.'


@app.put('/update-role-metadata')
async def update_role_metadata(player: Player):
    # get user to make sure they are still connected
    user = client.get_user(id=player.owner_id)

    if user is None:
        raise UserNotFound(player.owner_id)

    # get user role connection
    before = await user.fetch_role_connection()

    if before is None:
        raise RoleConnectionNotFound(player.owner_id)

    ## copy role connection to make changes
    role = before.copy()

    role.platform_username = player.display_name
    if player.competitive_rank is not None:
        role.platform_username += f' ({player.competitive_rank})'

    # edit metadata
    role.edit_metadata(key='matches', value=player.matches)
    role.edit_metadata(key='winrate', value=int(player.winrate))
    role.edit_metadata(key='combat_score', value=int(player.combat_score))
    role.edit_metadata(key='last_update', value=datetime.datetime.now())

    # new metadata
    role.add_or_edit_metadata(key='verified', value=player.verified)

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
async def is_authenticated(user_id: int):
    user = client.get_user(user_id)
    if user is None:
        raise UserNotFound(user_id)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={'status': 200, 'authenticated': await client.is_authenticated(user.get_token())},
    )
