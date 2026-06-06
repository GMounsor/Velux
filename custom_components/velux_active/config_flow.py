"""Config flow for Velux Active."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from pyatmo.exceptions import ApiError

from .api import (
    OAuthTokens,
    VeluxActiveCannotConnect,
    VeluxActiveClient,
    VeluxActiveInvalidAuth,
)
from .const import CONF_SIGN_KEY, CONF_SIGN_KEY_ID, DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
)


class VeluxActiveConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Velux Active."""

    VERSION = 1

    _username: str

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: Any) -> OptionsFlow:
        """Return the options flow handler."""
        return VeluxActiveOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._async_abort_entries_match({CONF_USERNAME: user_input[CONF_USERNAME]})
            try:
                title, tokens = await self._async_validate_input(user_input)
            except VeluxActiveInvalidAuth:
                errors["base"] = "invalid_auth"
            except (VeluxActiveCannotConnect, ApiError) as err:
                LOGGER.debug("Connection error validating Velux Active account: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:
                LOGGER.exception("Unexpected error validating Velux Active account")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=title,
                    data={**user_input, **tokens.as_storage_dict()},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a reauthorization flow request."""
        self._username = entry_data[CONF_USERNAME]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauthentication for an existing config entry."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            full_input = {
                CONF_USERNAME: self._username,
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            try:
                _, tokens = await self._async_validate_input(full_input)
            except VeluxActiveInvalidAuth:
                errors["base"] = "invalid_auth"
            except VeluxActiveCannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                LOGGER.exception("Unexpected error reauthenticating Velux Active account")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        **tokens.as_storage_dict(),
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={CONF_USERNAME: self._username},
            errors=errors,
        )

    async def _async_validate_input(
        self, user_input: Mapping[str, Any]
    ) -> tuple[str, OAuthTokens]:
        """Validate the credentials."""
        client = VeluxActiveClient(
            async_get_clientsession(self.hass),
            user_input[CONF_USERNAME],
            user_input[CONF_PASSWORD],
        )
        info = await client.async_validate()
        tokens = client.tokens
        if tokens is None:
            msg = "VELUX ACTIVE login did not return OAuth tokens"
            raise VeluxActiveCannotConnect(msg)
        return info, tokens


class VeluxActiveOptionsFlow(OptionsFlow):
    """Handle VELUX ACTIVE options (sign key configuration)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the options form."""
        errors: dict[str, str] = {}

        if user_input is not None:
            sign_key_hex = user_input.get(CONF_SIGN_KEY, "").strip()
            # Validate hex string if provided
            if sign_key_hex:
                try:
                    bytes.fromhex(sign_key_hex)
                except ValueError:
                    errors[CONF_SIGN_KEY] = "invalid_sign_key"

            if not errors:
                return self.async_create_entry(
                    data={
                        CONF_SIGN_KEY: sign_key_hex,
                        CONF_SIGN_KEY_ID: user_input.get(CONF_SIGN_KEY_ID, "").strip(),
                    }
                )

        current = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SIGN_KEY,
                        default=current.get(CONF_SIGN_KEY, ""),
                    ): str,
                    vol.Optional(
                        CONF_SIGN_KEY_ID,
                        default=current.get(CONF_SIGN_KEY_ID, ""),
                    ): str,
                }
            ),
            errors=errors,
        )
