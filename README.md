<h3 align="center">
	Discord Linked Roles OAuth2
</h3>
<h5 align="center">
  A basic wrapper for the Discord Linked Roles OAuth2 API.
</h5>

<p align="center">
    <img alt="Releases" src="https://img.shields.io/github/release/staciax/discord-linked-roles.svg?style=for-the-badge&logo=github&color=F2CDCD&logoColor=D9E0EE&labelColor=302D41"/></a>
	<a href="https://github.com/staciax/discord-linked-roles/stargazers"><img src="https://img.shields.io/github/stars/staciax/discord-linked-roles?colorA=363a4f&colorB=b7bdf8&style=for-the-badge"></a>
	<a href="https://github.com/staciax/discord-linked-roles/issues"><img src="https://img.shields.io/github/issues/staciax/discord-linked-roles?colorA=363a4f&colorB=f5a97f&style=for-the-badge"></a>
	<a href="https://github.com/staciax/discord-linked-roles/contributors"><img src="https://img.shields.io/github/contributors/staciax/discord-linked-roles?colorA=363a4f&colorB=a6da95&style=for-the-badge"></a>
</p>

<!-- https://github.com/catppuccin color style -->

## Installation
```sh
$ pip install -U linked-roles
```

## FastAPI Example:
```py
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from linked_roles import LinkedRolesOAuth2, RoleConnection, UserNotFound

app = FastAPI(title='Linked Roles')

client = LinkedRolesOAuth2(
    client_id='client_id',
    client_secret='client_secret',
    redirect_uri='http://localhost:8000/callback',
    # token='discord_token',
    scopes=('role_connection_write', 'identify'),
    state='cookie_secret'
)

@app.on_event('startup')
async def startup():
    await client.start()

@app.on_event('shutdown')
async def shutdown():
    await client.close()

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
        raise UserNotFound('User not found')

    role = await user.fetch_role_connection()
    
    if role is None:
        # set role connection
        role = RoleConnection(platform_name='VALORANT', platform_username=str(user))

        # add metadata
        role.add_metadata(key='matches', value=10)
        role.add_metadata(key='winrate', value=20)
        role.add_metadata(key='combat_score', value=30)

        # set role metadata
        await user.edit_role_connection(role)

    return 'Role metadata set successfully. Please check your Discord profile.'
```

## Register Example:
```py
import asyncio

from linked_roles import RoleMetadataType, LinkedRolesOAuth2, RoleMetadataRecord

async def main():

    client = LinkedRolesOAuth2(client_id='client_id', token='discord_token')

    async with client:

        records = (
            RoleMetadataRecord(
                key='matches',
                name='Matches',
                type=2,
            ),
            RoleMetadataRecord(
                key='winrate',
                name='Win Rate',
                type=RoleMetadataType.interger_greater_than_or_equal,  # Union Between int and RoleMetadataType
            ),
            RoleMetadataRecord(
                key='combat_score',
                name='Combat Score',
                description='Combat score this season', # description is optional (default: '...')
                type=RoleMetadataType.interger_greater_than_or_equal,
            )
        )

        records = await client.register_role_metadata(records=records, force=True)
        print(records)

if __name__ == '__main__':
    asyncio.run(main())

```

## Cookie secret can be generated with:
```py
import uuid
>> uuid.uuid4().hex
```
<!--
## More Examples:
- fastapi more examples: [examples](examples)
## TODO:
- [ ] more examples
- [ ] documentation
- [ ] database support (postgresql, sqlite, etc.) ?
- [ ] localizations support
-->

<!-- code style, inspiration is discord.py -->

## License
licensed under the [MIT license](LICENSE).
