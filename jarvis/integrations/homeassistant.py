"""
Home Assistant integration (smart home).

Talks to a Home Assistant instance over its REST API using a long-lived access
token. Exposes tools to list devices, read a device's state, and turn devices
on/off. Requires ``HOMEASSISTANT_URL`` and ``HOMEASSISTANT_TOKEN``.
"""

from __future__ import annotations

import re

from jarvis.integrations.base import (
    BaseIntegration,
    IntegrationAction,
    IntegrationStatus,
)
from jarvis.integrations.http import HttpClient
from jarvis.utils.exceptions import IntegrationError

# A valid Home Assistant entity id: "<domain>.<object_id>". Restricting the
# character set stops a model-supplied id from escaping the API path.
_ENTITY_RE = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")


class HomeAssistantIntegration(BaseIntegration):
    """Control a Home Assistant smart home via its REST API."""

    name = "homeassistant"
    description = "Control smart-home devices through Home Assistant."

    def __init__(self, base_url: str = "", token: str = "",
                http: HttpClient | None = None) -> None:
        super().__init__()
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._http = http or HttpClient()

    # -- config / lifecycle -------------------------------------------------

    def is_configured(self) -> bool:
        return bool(self._base_url and self._token)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def connect(self) -> IntegrationStatus:
        try:
            data = await self._http.get_json(
                f"{self._base_url}/api/", headers=self._headers()
            )
        except IntegrationError as exc:
            return self._mark_error(str(exc))
        return self._mark_connected(str(data.get("message", "connected")))

    # -- actions ------------------------------------------------------------

    def actions(self) -> list[IntegrationAction]:
        entity_param = {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "Entity id, e.g. 'light.kitchen'.",
                }
            },
            "required": ["entity_id"],
        }
        return [
            IntegrationAction(
                name="home_list_devices",
                description="List smart-home devices, optionally filtered by domain "
                            "(e.g. 'light', 'switch', 'climate').",
                parameters={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "Optional domain filter, e.g. 'light'.",
                        }
                    },
                },
                handler=self.list_devices,
            ),
            IntegrationAction(
                name="home_get_state",
                description="Get the current state of a smart-home device.",
                parameters=entity_param,
                handler=self.get_state,
            ),
            IntegrationAction(
                name="home_turn_on",
                description="Turn a smart-home device on.",
                parameters=entity_param,
                handler=self.turn_on,
            ),
            IntegrationAction(
                name="home_turn_off",
                description="Turn a smart-home device off.",
                parameters=entity_param,
                handler=self.turn_off,
            ),
        ]

    # -- handlers -----------------------------------------------------------

    async def list_devices(self, domain: str = "", **_: object) -> str:
        states = await self._http.get_json(
            f"{self._base_url}/api/states", headers=self._headers()
        )
        # /api/states returns a list; HttpClient types it loosely as dict.
        items = states if isinstance(states, list) else []
        entities = [s.get("entity_id", "") for s in items]
        if domain:
            entities = [e for e in entities if e.startswith(f"{domain}.")]
        if not entities:
            return "No matching devices found."
        shown = entities[:40]
        more = "" if len(entities) <= 40 else f" (+{len(entities) - 40} more)"
        return "Devices: " + ", ".join(shown) + more

    @staticmethod
    def _valid_entity(entity_id: str) -> bool:
        return bool(_ENTITY_RE.match(entity_id or ""))

    async def get_state(self, entity_id: str = "", **_: object) -> str:
        if not self._valid_entity(entity_id):
            return "Please provide a valid entity id (e.g. 'light.kitchen')."
        data = await self._http.get_json(
            f"{self._base_url}/api/states/{entity_id}", headers=self._headers()
        )
        return f"{entity_id} is {data.get('state', 'unknown')}."

    async def _call_service(self, entity_id: str, service: str) -> str:
        if not self._valid_entity(entity_id):
            return "Please provide a valid entity id (e.g. 'light.kitchen')."
        domain = entity_id.split(".", 1)[0]
        await self._http.post_json(
            f"{self._base_url}/api/services/{domain}/{service}",
            json={"entity_id": entity_id},
            headers=self._headers(),
        )
        return f"Done — {service.replace('_', ' ')} {entity_id}."

    async def turn_on(self, entity_id: str = "", **_: object) -> str:
        return await self._call_service(entity_id, "turn_on")

    async def turn_off(self, entity_id: str = "", **_: object) -> str:
        return await self._call_service(entity_id, "turn_off")
