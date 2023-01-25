# Copyright (c) 2023-present staciax
# Copyright (c) 2015-present Rapptz
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict, Tuple, Union

if TYPE_CHECKING:
    from aiohttp import ClientResponse


__all__: Tuple[str, ...] = ('json_or_text', 'MISSING')

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


# source: https://github.com/Rapptz/discord.py/blob/master/discord/utils.py
class _MissingSentinel:
    __slots__ = ()

    def __eq__(self, other) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __hash__(self) -> int:
        return 0

    def __repr__(self):
        return '...'


MISSING: Any = _MissingSentinel()
