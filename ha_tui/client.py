from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class Entity:
    entity_id: str
    name: str
    state: str
    attributes: dict[str, Any]
    domain: str = field(init=False)

    def __post_init__(self) -> None:
        self.domain = self.entity_id.split(".")[0]


class HAClient:
    def __init__(self, url: str, token: str) -> None:
        self.url = url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _make_entity(self, raw: dict[str, Any]) -> Entity:
        return Entity(
            entity_id=raw["entity_id"],
            name=raw["attributes"].get("friendly_name", raw["entity_id"]),
            state=raw["state"],
            attributes=raw["attributes"],
        )

    async def get_states(self) -> list[Entity]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.url}/api/states",
                headers=self._headers,
                timeout=10,
            )
            r.raise_for_status()
        return [
            self._make_entity(s)
            for s in r.json()
            if s["entity_id"].split(".")[0] in ("light", "climate")
        ]

    async def get_entity(self, entity_id: str) -> Entity:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.url}/api/states/{entity_id}",
                headers=self._headers,
                timeout=10,
            )
            r.raise_for_status()
        return self._make_entity(r.json())

    async def get_area_map(self) -> dict[str, str]:
        """Return {entity_id: area_name} for all light and climate entities."""
        template = (
            "{% for s in states.light %}"
            "{{ s.entity_id }}|{{ area_name(s.entity_id) | default('') }}\n"
            "{% endfor %}"
            "{% for s in states.climate %}"
            "{{ s.entity_id }}|{{ area_name(s.entity_id) | default('') }}\n"
            "{% endfor %}"
        )
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.url}/api/template",
                headers=self._headers,
                json={"template": template},
                timeout=10,
            )
            r.raise_for_status()
        result: dict[str, str] = {}
        for line in r.text.strip().splitlines():
            if "|" in line:
                entity_id, area = line.split("|", 1)
                result[entity_id.strip()] = area.strip()
        return result

    async def test_connection(self) -> None:
        """Verify URL and token are valid. Raises on any failure."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.url}/api/",
                headers=self._headers,
                timeout=10,
            )
            r.raise_for_status()

    async def get_scenes(self) -> list[Entity]:
        """Return all scene entities, sorted by name."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.url}/api/states",
                headers=self._headers,
                timeout=10,
            )
            r.raise_for_status()
        return sorted(
            (
                self._make_entity(s)
                for s in r.json()
                if s["entity_id"].split(".")[0] == "scene"
            ),
            key=lambda e: e.name,
        )

    async def call_service(
        self, domain: str, service: str, data: dict[str, Any]
    ) -> None:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.url}/api/services/{domain}/{service}",
                headers=self._headers,
                json=data,
                timeout=10,
            )
            r.raise_for_status()
