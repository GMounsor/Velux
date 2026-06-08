"""The Velux Active integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OAuthTokens, VeluxActiveClient
from .const import CONF_SIGN_KEY, CONF_SIGN_KEY_ID, LOGGER, PLATFORMS
from .coordinator import VeluxActiveDataUpdateCoordinator

type VeluxActiveConfigEntry = ConfigEntry[VeluxActiveDataUpdateCoordinator]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VeluxActiveConfigEntry,
) -> bool:
    """Set up Velux Active from a config entry."""

    def _handle_tokens(tokens: OAuthTokens) -> None:
        token_data = tokens.as_storage_dict()
        if all(entry.data.get(key) == value for key, value in token_data.items()):
            return
        hass.config_entries.async_update_entry(entry, data={**entry.data, **token_data})

    # Read optional sign key from options (hex-encoded bytes).
    sign_key_hex = entry.options.get(CONF_SIGN_KEY, "").strip()
    sign_key: bytes | None = bytes.fromhex(sign_key_hex) if sign_key_hex else None
    sign_key_id: str | None = entry.options.get(CONF_SIGN_KEY_ID, "").strip() or None

    coordinator = VeluxActiveDataUpdateCoordinator(
        hass,
        entry,
        VeluxActiveClient(
            async_get_clientsession(hass),
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            initial_tokens=OAuthTokens.from_mapping(entry.data),
            token_updated=_handle_tokens,
            sign_key=sign_key,
            sign_key_id=sign_key_id,
        ),
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload the integration when the user saves new options (e.g. sign key).
    entry.async_on_unload(
        entry.add_update_listener(
            lambda _hass, _entry: _hass.config_entries.async_reload(_entry.entry_id)
        )
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: VeluxActiveConfigEntry,
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
