"""Sensor platform for Velux Active.

Exposes indoor climate measurements from VELUX NXS room sensors:
  - Temperature
  - Humidity

Data is sourced from pyatmo Room objects populated during the homestatus poll.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONTROL_URL, DOMAIN, MANUFACTURER
from .coordinator import VeluxActiveConfigEntry, VeluxActiveDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class VeluxRoomSensorDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with the pyatmo Room attribute name."""

    room_attr: str = ""


ROOM_SENSOR_DESCRIPTIONS: tuple[VeluxRoomSensorDescription, ...] = (
    VeluxRoomSensorDescription(
        key="temperature",
        room_attr="therm_measured_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    VeluxRoomSensorDescription(
        key="humidity",
        room_attr="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VeluxActiveConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up VELUX room sensors from a config entry."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = []

    for room_id in sorted(coordinator.data.rooms):
        room = coordinator.data.rooms[room_id]
        for description in ROOM_SENSOR_DESCRIPTIONS:
            if getattr(room, description.room_attr, None) is not None:
                entities.append(
                    VeluxActiveRoomSensor(coordinator, room_id, description)
                )

    async_add_entities(entities)


class VeluxActiveRoomSensor(
    CoordinatorEntity[VeluxActiveDataUpdateCoordinator], SensorEntity
):
    """A sensor entity for a VELUX ACTIVE room measurement (NXS climate sensor data)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VeluxActiveDataUpdateCoordinator,
        room_id: str,
        description: VeluxRoomSensorDescription,
    ) -> None:
        """Initialize the room sensor."""
        super().__init__(coordinator)
        self._room_id = room_id
        self.entity_description = description
        self._attr_unique_id = f"room_{room_id}_{description.key}"

        room = coordinator.data.rooms[room_id]
        self._attr_device_info = DeviceInfo(
            configuration_url=CONTROL_URL,
            identifiers={(DOMAIN, f"room_{room_id}")},
            manufacturer=MANUFACTURER,
            model="NXS Indoor Climate Sensor",
            name=room.name,
        )

    @property
    def _room(self) -> Any:
        """Return the current pyatmo Room object."""
        return self.coordinator.data.rooms.get(self._room_id)

    @property
    def native_value(self) -> float | int | None:
        """Return the sensor reading."""
        room = self._room
        if room is None:
            return None
        return getattr(room, self.entity_description.room_attr, None)

    @property
    def available(self) -> bool:
        """Return availability based on room presence and coordinator health."""
        return (
            super().available
            and self._room is not None
            and self.native_value is not None
        )
