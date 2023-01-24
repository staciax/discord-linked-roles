# Copyright (c) 2023-present staciax
# Licensed under the MIT license. Refer to the LICENSE file in the project root for more information.

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Tuple, Union

if TYPE_CHECKING:
    from aiohttp import ClientResponse

__all__: Tuple[str, ...] = (
    'HTTPException',
    'Unauthorized',
    'NotFound',
    'InternalServerError',
    'RateLimited',
    'UserNotFound',
    'OAuth2Unauthorized',
)


class HTTPException(Exception):
    """Base exception class for all HTTP related errors."""

    def __init__(self, response: ClientResponse, message: Union[str, Dict[str, Any]]) -> None:
        self.response: ClientResponse = response
        self.message: Union[str, Dict[str, Any]] = message
        self.status: int = response.status
        super().__init__(message)


class Unauthorized(HTTPException):
    """Exception that's thrown when the HTTP request returns a 401 status code."""

    pass


class NotFound(HTTPException):
    """Exception that's thrown when the HTTP request returns a 404 status code."""

    pass


class InternalServerError(HTTPException):
    """Exception that's thrown when the HTTP request returns a 500 status code."""

    pass


class RateLimited(HTTPException):
    """Exception that's thrown when the HTTP request returns a 429 status code."""

    def __init__(self, response: ClientResponse, message: str) -> None:
        self.retry_after = message.get('retry_after', 0) if isinstance(message, dict) else 0
        super().__init__(response, message)


class UserNotFound(Exception):
    """Exception that's thrown when the user is not found in the database."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class OAuth2Unauthorized(Exception):
    """Exception that's thrown when the OAuth2 token is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
