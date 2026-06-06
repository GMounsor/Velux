"""Binary sensor platform for Velux Active.

Exposes two binary sensor types:
  - Rain detection (one per NXG gateway, from the gateway's is_raining flag)
  - Cover open/closed (one per NXO cover, derived from current position)
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import VeluxActiveConfigEntry
from .entity import VeluxActiveEntity, VeluxActiveGatewayEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VeluxActiveConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up VELUX binary sensors from a config entry."""
    coordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = []

    # Rain sensor for each gateway
    for gw_id in sorted(coordinator.data.gateways):
        entities.append(VeluxActiveRainSensor(coordinator, gw_id))

    # Open/closed sensor for each cover
    for cover_id in sorted(coordinator.data.covers):
        entities.append(VeluxActiveOpenSensor(coordinator, cover_id))

    async_add_entities(entities)


class VeluxActiveRainSensor(VeluxActiveGatewayEntity, BinarySensorEntity):
    """Rain detection binary sensor, sourced from an NXG gateway's is_raining flag.

    The gateway raises this flag when it detects rain, which causes it to stop
    automatic position adjustments. Expose it so automations can react.
    True  = rain detected.
    False = no rain detected.
    """

    _attr_device_class = BinarySensorDeviceClass.MOISTURE

    def __init__(self, coordinator, module_id: str) -> None:
        """Initialize the rain sensor."""
        super().__init__(coordinator, module_id)
        self._attr_unique_id = f"{module_id}_rain"

    @property
    def name(self) -> str:
        """Return the entity name."""
        return "Rain"

    @property
    def is_on(self) -> bool | None:
        """Return True when rain is detected."""
        return self.gateway.is_raining


class VeluxActiveOpenSensor(VeluxActiveEntity, BinarySensorEntity):
    """Open/closed binary sensor, sourced from an NXO cover's current position.

    True  = cover is open (position > 0).
    False = cover is fully closed (position == 0).
    None  = position unknown.

    This is useful for roof windows and vents where knowing the open state
    matters for ventilation and weather automations.
    """

    _attr_device_class = BinarySensorDeviceClass.OPENING

    def __init__(self, coordinator, module_id: str) -> None:
        """Initialize the open sensor."""
        super().__init__(coordinator, module_id)
        self._attr_unique_id = f"{module_id}_open"

    @property
    def name(self) -> str:
        """Return the entity name."""
        return "Open"

    @property
    def is_on(self) -> bool | None:
        """Return True when the cover is not fully closed."""
        position = self.module.current_position
        if position is None:
            return None
        return position > 0
