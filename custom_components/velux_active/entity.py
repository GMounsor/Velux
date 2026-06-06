"""Base entities for Velux Active."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONTROL_URL, DOMAIN, MANUFACTURER
from .coordinator import VeluxActiveDataUpdateCoordinator


class VeluxActiveEntity(CoordinatorEntity[VeluxActiveDataUpdateCoordinator]):
    """Shared entity for VELUX ACTIVE cover/opener devices (NXO)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VeluxActiveDataUpdateCoordinator,
        module_id: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._module_id = module_id
        self._attr_unique_id = module_id
        self._attr_name = None

    @property
    def module(self):
        """Return the current pyatmo NXO module."""
        return self.coordinator.data.covers[self._module_id]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the cover module."""
        module = self.module
        model = (getattr(module, "velux_type", None) or "cover").replace("_", " ").title()
        return DeviceInfo(
            configuration_url=CONTROL_URL,
            identifiers={(DOMAIN, module.entity_id)},
            manufacturer=MANUFACTURER,
            model=model,
            name=module.name,
            sw_version=str(getattr(module, "firmware_revision", "")) or None,
        )


class VeluxActiveGatewayEntity(CoordinatorEntity[VeluxActiveDataUpdateCoordinator]):
    """Shared entity for VELUX ACTIVE gateway devices (NXG)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VeluxActiveDataUpdateCoordinator,
        module_id: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._module_id = module_id
        self._attr_unique_id = module_id
        self._attr_name = None

    @property
    def gateway(self):
        """Return the current pyatmo NXG gateway module."""
        return self.coordinator.data.gateways[self._module_id]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the gateway module."""
        gw = self.gateway
        return DeviceInfo(
            configuration_url=CONTROL_URL,
            identifiers={(DOMAIN, gw.entity_id)},
            manufacturer=MANUFACTURER,
            model="NXG Gateway",
            name=gw.name,
            sw_version=str(getattr(gw, "firmware_revision", "")) or None,
        )
