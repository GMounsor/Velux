"""The Velux Active integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OAuthTokens, VeluxActiveClient
from .const import DOMAIN, LOGGER, PLATFORMS
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

    coordinator = VeluxActiveDataUpdateCoordinator(
        hass,
        entry,
        VeluxActiveClient(
            async_get_clientsession(hass),
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            initial_tokens=OAuthTokens.from_mapping(entry.data),
            token_updated=_handle_tokens,
        ),
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _handle_retrieve_keys(_call: ServiceCall) -> None:
        """Service handler: fire retrieve_key for all gateways and log the response."""
        LOGGER.warning(
            "VELUX retrieve_keys service called — check logs for HashSignKey and SignKeyId"
        )
        await coordinator.client.async_retrieve_keys()

    async def _handle_dump_raw_data(_call: ServiceCall) -> None:
        """Service handler: dump raw homesdata and homestatus API responses."""
        LOGGER.warning("VELUX dump_raw_data service called — dumping full API responses")
        await coordinator.client.async_dump_raw_data()

    hass.services.async_register(DOMAIN, "retrieve_keys", _handle_retrieve_keys)
    hass.services.async_register(DOMAIN, "dump_raw_data", _handle_dump_raw_data)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: VeluxActiveConfigEntry,
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
