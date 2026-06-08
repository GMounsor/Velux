"""API client for Velux Active."""

from __future__ import annotations

import base64
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from json import JSONDecodeError
import hashlib
import hmac
import time
from typing import Any

import aiohttp
from pyatmo.account import AsyncAccount
from pyatmo.auth import AbstractAsyncAuth
from pyatmo.const import AUTH_REQ_ENDPOINT, SETSTATE_ENDPOINT
from pyatmo.enums import ScheduleType
from pyatmo.exceptions import NoDeviceError
from pyatmo.home import Home
from pyatmo.modules import NXG, NXO
from pyatmo.room import Room

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    LOGGER,
)

# Work around pyatmo 9.4.0 until https://github.com/jabesq-org/pyatmo/pull/564 is released.
# Some pyatmo versions use AUTO, others may not have it — guard both cases.
try:
    _algo_fallback = getattr(ScheduleType, "AUTO", None) or next(iter(ScheduleType))
    ScheduleType._value2member_map_.setdefault("algo", _algo_fallback)
except Exception:  # noqa: BLE001
    pass

DEFAULT_CLIENT_ID = "5931426da127d981e76bdd3f"
DEFAULT_CLIENT_SECRET = "6ae2d89d15e767ae5c56b456b452d319"
DEFAULT_APP_VERSION = "791302006"
DEFAULT_SCOPE = "velux_scopes"
DEFAULT_TIMEOUT = 10.0
DEFAULT_USER_PREFIX = "velux"


class VeluxActiveError(Exception):
    """Base exception for the integration."""


class VeluxActiveCannotConnect(VeluxActiveError):
    """Raised when the API cannot be reached."""


class VeluxActiveInvalidAuth(VeluxActiveError):
    """Raised when credentials are invalid."""


@dataclass(slots=True)
class OAuthTokens:
    """Container for OAuth token data."""

    access_token: str
    refresh_token: str | None
    expires_at: int | None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> OAuthTokens | None:
        """Build tokens from stored config entry data."""
        access_token = str(data.get(CONF_ACCESS_TOKEN) or "")
        refresh_token = data.get(CONF_REFRESH_TOKEN)
        expires_at = data.get(CONF_TOKEN_EXPIRES_AT)

        if not access_token and not refresh_token:
            return None

        return cls(
            access_token=access_token,
            refresh_token=str(refresh_token) if refresh_token else None,
            expires_at=int(expires_at) if expires_at is not None else None,
        )

    def as_storage_dict(self) -> dict[str, Any]:
        """Return a serializable token payload for config entry storage."""
        return {
            CONF_ACCESS_TOKEN: self.access_token,
            CONF_REFRESH_TOKEN: self.refresh_token,
            CONF_TOKEN_EXPIRES_AT: self.expires_at,
        }


@dataclass(slots=True)
class VeluxActiveData:
    """Current snapshot of the Velux account."""

    user: str | None
    homes: dict[str, Home]
    covers: dict[str, NXO]
    gateways: dict[str, NXG]
    rooms: dict[str, Room]


class VeluxActiveAuth(AbstractAsyncAuth):
    """pyatmo auth adapter using the VELUX password grant."""

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        *,
        username: str,
        password: str,
        initial_tokens: OAuthTokens | None = None,
        token_updated: Callable[[OAuthTokens], None] | None = None,
    ) -> None:
        """Initialize the auth adapter."""
        super().__init__(websession)
        self._username = username
        self._password = password
        self._token_updated = token_updated
        self._tokens: OAuthTokens | None = initial_tokens

    async def async_get_access_token(self) -> str:
        """Return a valid access token for pyatmo requests."""
        if self._tokens and self._tokens.access_token and self._is_token_valid(self._tokens):
            return self._tokens.access_token

        if self._tokens and self._tokens.refresh_token:
            try:
                await self.async_refresh()
            except VeluxActiveInvalidAuth:
                await self.async_login()
        else:
            await self.async_login()

        if self._tokens is None:
            msg = "No access token available"
            raise VeluxActiveInvalidAuth(msg)
        return self._tokens.access_token

    async def async_login(self) -> OAuthTokens:
        """Authenticate using email and password."""
        return await self._async_request_tokens(
            {
                "grant_type": "password",
                "username": self._username,
                "password": self._password,
                "scope": DEFAULT_SCOPE,
                "user_prefix": DEFAULT_USER_PREFIX,
            }
        )

    async def async_refresh(self) -> OAuthTokens:
        """Refresh the current access token."""
        if self._tokens is None or not self._tokens.refresh_token:
            msg = "Refresh token is not available"
            raise VeluxActiveInvalidAuth(msg)

        return await self._async_request_tokens(
            {
                "grant_type": "refresh_token",
                "refresh_token": self._tokens.refresh_token,
            }
        )

    async def process_response(
        self,
        response: aiohttp.ClientResponse,
        url: str,
    ) -> aiohttp.ClientResponse:
        """Process API responses and log setstate body errors."""
        response = await super().process_response(response, url)
        if not url.endswith(SETSTATE_ENDPOINT):
            return response

        try:
            raw: Any = await response.json(content_type=None)
        except (aiohttp.ContentTypeError, JSONDecodeError):
            return response

        body = raw.get("body") if isinstance(raw, dict) else None
        errors = body.get("errors") if isinstance(body, dict) else None
        if errors:
            LOGGER.warning(
                "VELUX Active setstate response returned API errors: "
                "api_errors=%s api_response=%s",
                errors,
                raw,
            )

        return response

    def _is_token_valid(self, tokens: OAuthTokens) -> bool:
        """Return whether the current token is still valid."""
        return tokens.expires_at is None or int(time.time()) < (tokens.expires_at - 60)

    @property
    def tokens(self) -> OAuthTokens | None:
        """Return the latest OAuth token set."""
        return self._tokens

    async def _async_request_tokens(self, payload: dict[str, str]) -> OAuthTokens:
        """Request OAuth tokens."""
        url = f"{self.base_url}{AUTH_REQ_ENDPOINT}"
        data = {
            "client_id": DEFAULT_CLIENT_ID,
            "client_secret": DEFAULT_CLIENT_SECRET,
            "app_version": DEFAULT_APP_VERSION,
            **payload,
        }

        try:
            async with self.websession.post(
                url,
                data=data,
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
            ) as response:
                try:
                    raw: Any = await response.json(content_type=None)
                except aiohttp.ContentTypeError:
                    raw = {"raw": await response.text()}
        except (aiohttp.ClientError, TimeoutError) as err:
            raise VeluxActiveCannotConnect(str(err)) from err

        if not response.ok:
            self._raise_for_auth_response(response.status, raw)

        if not isinstance(raw, dict) or "access_token" not in raw:
            msg = f"Unexpected token response from {url}"
            raise VeluxActiveCannotConnect(msg)

        issued_at = int(time.time())
        expires_in = raw.get("expires_in", raw.get("expire_in"))
        expires_at = (
            issued_at + int(expires_in) if expires_in is not None else None
        )
        new_tokens = OAuthTokens(
            access_token=str(raw["access_token"]),
            refresh_token=(
                str(raw["refresh_token"]) if raw.get("refresh_token") else None
            ),
            expires_at=expires_at,
        )
        self._tokens = new_tokens
        if self._token_updated:
            self._token_updated(new_tokens)
        return self._tokens

    def _raise_for_auth_response(self, status: int, raw: Any) -> None:
        """Raise a typed exception for an auth response."""
        error = ""
        if isinstance(raw, dict):
            error = str(raw.get("error") or raw.get("message") or "")

        if status in {400, 401} or error == "invalid_grant":
            raise VeluxActiveInvalidAuth(error or "Invalid credentials")

        raise VeluxActiveCannotConnect(error or f"Authentication failed with {status}")


class VeluxActiveClient:
    """Thin client combining the VELUX auth flow with pyatmo."""

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        username: str,
        password: str,
        *,
        initial_tokens: OAuthTokens | None = None,
        token_updated: Callable[[OAuthTokens], None] | None = None,
        sign_key: bytes | None = None,
        sign_key_id: str | None = None,
    ) -> None:
        """Initialize the client."""
        self._auth = VeluxActiveAuth(
            websession,
            username=username,
            password=password,
            initial_tokens=initial_tokens,
            token_updated=token_updated,
        )
        self._account = AsyncAccount(self._auth)
        self._username = username
        self._sign_key = sign_key
        self._sign_key_id = sign_key_id
        # Per-module nonce counters; start at 0 each session.
        self._nonces: dict[str, int] = {}

    @property
    def has_sign_key(self) -> bool:
        """Return True if a HashSignKey has been configured."""
        return self._sign_key is not None and self._sign_key_id is not None

    def _compute_signature(
        self, value: int, timestamp: int, nonce: int, device_id: str
    ) -> str:
        """Compute HMAC-SHA512 for a target_position command.

        Formula (confirmed from Android smali hm4.smali / test against live API):
            HMAC-SHA512(HashSignKey, "target_position" + str(value) +
                        str(timestamp) + str(nonce) + device_id)
        Result is URL-safe base64 WITH padding (Android Base64.NO_WRAP|URL_SAFE).
        """
        msg = f"target_position{value}{timestamp}{nonce}{device_id}".encode()
        digest = hmac.new(self._sign_key, msg, hashlib.sha512).digest()  # type: ignore[arg-type]
        return base64.urlsafe_b64encode(digest).decode()  # keep == padding

    async def async_set_position_signed(
        self, home: Any, module_id: str, position: int
    ) -> bool:
        """Send a signed target_position command for a velux_type=window module.

        Returns True if the API accepted the command (status == "ok").
        Raises ApiError on HTTP-level failures (propagated from pyatmo).
        """
        import json as _json

        nonce = self._nonces.get(module_id, 0)
        self._nonces[module_id] = nonce + 1
        timestamp = int(time.time())
        sig = self._compute_signature(position, timestamp, nonce, module_id)

        module = home.modules[module_id]
        payload = {
            "json": {
                "app_identifier": "app_velux",
                "home": {
                    "id": home.entity_id,
                    "modules": [
                        {
                            "id": module_id,
                            "bridge": module.bridge,
                            "target_position": position,
                            "nonce": nonce,
                            "timestamp": timestamp,
                            "sign_key_id": self._sign_key_id,
                            "hash_target_position": sig,
                        }
                    ],
                },
            }
        }
        LOGGER.debug(
            "VELUX signed setstate: module_id=%s position=%s nonce=%s sign_key_id=%s",
            module_id,
            position,
            nonce,
            self._sign_key_id,
        )
        resp = await home.auth.async_post_api_request(
            endpoint=SETSTATE_ENDPOINT,
            params=payload,
        )
        raw: Any = await resp.json(content_type=None)
        LOGGER.debug("VELUX signed setstate response: %s", _json.dumps(raw))
        if isinstance(raw, dict):
            return raw.get("status") == "ok"
        return False

    async def async_validate(self) -> str:
        """Validate credentials by fetching topology only (no status poll needed)."""
        await self._account.async_update_topology()
        home_names = [home.name for home in self._account.homes.values()]
        return home_names[0] if len(home_names) == 1 else self._username

    async def async_update(self) -> VeluxActiveData:
        """Refresh topology and current status."""
        await self._account.async_update_topology()
        for home_id in list(self._account.homes):
            try:
                await self._account.async_update_status(home_id)
            except NoDeviceError as err:
                # Gateway may be temporarily unreachable; keep going with topology data.
                LOGGER.debug(
                    "Status poll returned no devices for home %s (gateway may be offline): %s",
                    home_id,
                    err,
                )

        covers: dict[str, NXO] = {}
        gateways: dict[str, NXG] = {}
        rooms: dict[str, Room] = {}

        for home in self._account.homes.values():
            for module_id, module in home.modules.items():
                if isinstance(module, NXO):
                    covers[module_id] = module
                elif isinstance(module, NXG):
                    gateways[module_id] = module
            for room_id, room in home.rooms.items():
                rooms[room_id] = room

        return VeluxActiveData(
            user=self._account.user,
            homes=dict(self._account.homes),
            covers=covers,
            gateways=gateways,
            rooms=rooms,
        )

    async def async_websocket_test(self, ws_token: str) -> None:
        """Connect to VELUX WebSocket, call retrieve_key, and log all messages.

        Used by the velux_active.websocket_test diagnostic service to check
        whether the HashSignKey is delivered via WebSocket push.
        """
        import asyncio
        import json as _json

        ws_url = "wss://app-ws.velux-active.com/ws/"
        headers = {"Authorization": f"Bearer {ws_token}"}

        LOGGER.warning("VELUX WebSocket connecting to %s", ws_url)
        try:
            async with self._auth.websession.ws_connect(
                ws_url,
                headers=headers,
                heartbeat=30,
                ssl=True,
            ) as ws:
                LOGGER.warning("VELUX WebSocket connected — listening for initial message")

                # Capture first message (may contain initial state / key data)
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
                    LOGGER.warning("VELUX WebSocket initial message type=%s data=%s", msg.type, msg.data)
                except asyncio.TimeoutError:
                    LOGGER.warning("VELUX WebSocket no initial message within 5s")

                # Call retrieve_key for each gateway
                for home in self._account.homes.values():
                    for module_id, module in home.modules.items():
                        if not isinstance(module, NXG):
                            continue
                        LOGGER.warning(
                            "VELUX WebSocket calling retrieve_key home_id=%s bridge_id=%s",
                            home.entity_id,
                            module_id,
                        )
                        resp = await home.auth.async_post_api_request(
                            endpoint=SETSTATE_ENDPOINT,
                            params={
                                "json": {
                                    "app_identifier": "app_velux",
                                    "home": {
                                        "id": home.entity_id,
                                        "modules": [{"id": module_id, "retrieve_key": True}],
                                    },
                                }
                            },
                        )
                        raw: Any = await resp.json(content_type=None)
                        LOGGER.warning("VELUX retrieve_key HTTP: %s", _json.dumps(raw))

                # Listen for 15 seconds for any pushed key data
                LOGGER.warning("VELUX WebSocket listening 15s for key push...")
                end = asyncio.get_event_loop().time() + 15
                while asyncio.get_event_loop().time() < end:
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=3.0)
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            LOGGER.warning("VELUX WebSocket push: %s", msg.data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            LOGGER.warning("VELUX WebSocket closed/error: %s", msg.type)
                            break
                    except asyncio.TimeoutError:
                        pass
                LOGGER.warning("VELUX WebSocket test complete")
        except Exception as err:
            LOGGER.warning("VELUX WebSocket error: %s", err)

    async def async_retrieve_keys(self) -> None:
        """Call retrieve_key for every gateway and log the raw response.

        Used by the velux_active.retrieve_keys diagnostic service.
        The response may contain the HashSignKey needed for window open commands.
        """
        import json as _json

        for home in self._account.homes.values():
            for module_id, module in home.modules.items():
                if not isinstance(module, NXG):
                    continue
                LOGGER.warning(
                    "VELUX retrieve_key request: home_id=%s bridge_id=%s",
                    home.entity_id,
                    module_id,
                )
                try:
                    resp = await home.auth.async_post_api_request(
                        endpoint=SETSTATE_ENDPOINT,
                        params={
                            "json": {
                                "app_identifier": "app_velux",
                                "home": {
                                    "id": home.entity_id,
                                    "modules": [{"id": module_id, "retrieve_key": True}],
                                },
                            }
                        },
                    )
                    try:
                        raw: Any = await resp.json(content_type=None)
                    except Exception:
                        raw = await resp.text()
                    LOGGER.warning(
                        "VELUX retrieve_key response: status=%s body=%s",
                        resp.status,
                        _json.dumps(raw) if isinstance(raw, dict) else raw,
                    )
                except Exception as err:
                    LOGGER.warning("VELUX retrieve_key error: %s", err)

    async def async_dump_raw_data(self) -> None:
        """Fetch and log raw API responses including getconfigs.

        Used by the velux_active.dump_raw_data diagnostic service to surface
        any key or security data that pyatmo doesn't expose.
        """
        import asyncio
        import json as _json
        from pyatmo.const import GETHOMESDATA_ENDPOINT, GETHOMESTATUS_ENDPOINT

        _GETCONFIGS_ENDPOINT = "syncapi/v1/getconfigs"
        _VELUX_BASE = "https://app.netatmo.net"

        # homesdata
        try:
            resp = await self._auth.async_post_api_request(
                endpoint=GETHOMESDATA_ENDPOINT,
            )
            raw: Any = await resp.json(content_type=None)
            LOGGER.warning("VELUX raw homesdata: %s", _json.dumps(raw))
        except Exception as err:
            LOGGER.warning("VELUX homesdata error: %s", err)

        await asyncio.sleep(1)

        for home in self._account.homes.values():
            # homestatus
            try:
                resp = await self._auth.async_post_api_request(
                    endpoint=GETHOMESTATUS_ENDPOINT,
                    params={"home_id": home.entity_id},
                )
                raw = await resp.json(content_type=None)
                LOGGER.warning(
                    "VELUX raw homestatus home_id=%s: %s",
                    home.entity_id,
                    _json.dumps(raw),
                )
            except Exception as err:
                LOGGER.warning("VELUX homestatus error home_id=%s: %s", home.entity_id, err)

            await asyncio.sleep(1)

            # getconfigs — may contain security/key configuration
            try:
                resp = await self._auth.async_post_request(
                    url=f"{_VELUX_BASE}/{_GETCONFIGS_ENDPOINT}",
                    params={"home_id": home.entity_id},
                )
                raw = await resp.json(content_type=None)
                LOGGER.warning(
                    "VELUX raw getconfigs home_id=%s: %s",
                    home.entity_id,
                    _json.dumps(raw),
                )
            except Exception as err:
                LOGGER.warning("VELUX getconfigs error home_id=%s: %s", home.entity_id, err)

    @property
    def tokens(self) -> OAuthTokens | None:
        """Return the latest OAuth token set."""
        return self._auth.tokens
