import asyncio

import config

from linked_roles import LinkedRolesOAuth2, RoleMetadataRecord, RoleMetadataType


async def main():

    client = LinkedRolesOAuth2(client_id=config.DISCORD_CLIENT_ID, token=config.DISCORD_TOKEN)

    async with client:

        records = (
            RoleMetadataRecord(
                key='matches',
                name='Matches',
                description='Number of matches this season',
                type=2,
            ),
            RoleMetadataRecord(
                key='winrate',
                name='Win Rate',
                description='Win rate this season',
                type=RoleMetadataType.interger_greater_than_or_equal,
            ),
            RoleMetadataRecord(
                key='combat_score',
                name='Combat Score',
                description='Combat score this season',
                type=RoleMetadataType.interger_greater_than_or_equal,
            ),
            RoleMetadataRecord(
                key='last_update',
                name='Last Update',
                description='Last time this data was updated',
                type=RoleMetadataType.datetime_less_than_or_equal,
            ),
            RoleMetadataRecord(
                key='verified',
                name='Verified',
                description='Verified role',
                type=RoleMetadataType.boolean_equal,
            ),
        )

        records = await client.register_role_metadata(records=records, force=True)
        print(records)


if __name__ == '__main__':
    asyncio.run(main())
