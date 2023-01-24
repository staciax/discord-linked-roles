# Copyright (c) 2023-present staciax
# Copyright (c) 2015-present Rapptz
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict, Union

if TYPE_CHECKING:
    from aiohttp import ClientResponse

# source: https://github.com/Rapptz/discord.py/blob/master/discord/http.py
async def json_or_text(response: ClientResponse) -> Union[Dict[str, Any], str]:
    text = await response.text(encoding="utf-8")
    try:
        if response.headers['content-type'] == 'application/json':
            return json.loads(text)
    except KeyError:
        # thanks cloudflare
        pass

    return text
