from __future__ import annotations

from collections import defaultdict

from textual import events, work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.message import Message
from textual.widgets import (
    Button,
    ContentSwitcher,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
    Switch,
    Tab,
    Tabs,
)

from .client import Entity, HAClient
from .config import Config
from .settings import SettingsScreen
from .themes import DEFAULT_THEME, THEMES
from .widgets import BrightnessPicker, ColorPicker, ColorTempPicker

_COLOR_MODES = {"hs", "rgb", "xy", "rgbw", "rgbww"}


def _err(exc: Exception) -> str:
    """Return a non-empty error string — httpx errors often stringify to ''."""
    return str(exc) or type(exc).__name__


def _entity_state_str(entity: Entity) -> str:
    state = entity.state
    if entity.domain == "light" and state == "on":
        b = entity.attributes.get("brightness")
        return f"ONLINE  {round(b / 255 * 100)}%" if b is not None else "ONLINE"
    elif entity.domain == "light":
        return "OFFLINE"
    elif entity.domain == "climate":
        t = entity.attributes.get("current_temperature")
        return f"{state.upper()}  {t}°" if t is not None else state.upper()
    return state


# ── Sidebar list widgets ───────────────────────────────────────────────────

class AreaHeader(ListItem):
    def __init__(self, name: str) -> None:
        super().__init__()
        self._area_name = name

    def compose(self) -> ComposeResult:
        yield Label(f"── {self._area_name.upper()} ──", classes="area-header-label")


class EntityItem(ListItem):
    def __init__(self, entity: Entity) -> None:
        super().__init__()
        self.entity = entity

    def compose(self) -> ComposeResult:
        yield Label(f"> {self.entity.name}", classes="item-name")
        yield Label(_entity_state_str(self.entity), classes="item-state")


# ── Detail panels ──────────────────────────────────────────────────────────

class LightPanel(Static):
    class StateChanged(Message):
        pass

    def __init__(self, entity: Entity, client: HAClient) -> None:
        super().__init__()
        self._entity = entity
        self._client = client
        self._updating = False

    def _supports_color(self) -> bool:
        modes = self._entity.attributes.get("supported_color_modes", [])
        return bool(_COLOR_MODES & set(modes))

    def _supports_color_temp(self) -> bool:
        modes = self._entity.attributes.get("supported_color_modes", [])
        return "color_temp" in modes

    def compose(self) -> ComposeResult:
        e = self._entity
        is_on = e.state == "on"
        b = e.attributes.get("brightness", 255)
        brightness_pct = round(b / 255 * 100) if b else 0

        yield Label(f"// {e.name.upper()} //", id="panel-title")
        yield Label(f">> {'ONLINE' if is_on else 'OFFLINE'}", id="panel-status")

        with Horizontal(classes="control-row"):
            yield Label("PWR", classes="control-label")
            yield Switch(value=is_on, id="light-switch")

        yield BrightnessPicker(initial_brightness=float(brightness_pct), id="brightness-picker")

        if self._supports_color():
            hs = e.attributes.get("hs_color") or [0, 100]
            yield Label("── COLOR ──────────────", classes="section-divider")
            yield ColorPicker(
                initial_hue=float(hs[0]),
                initial_sat=float(hs[1]),
                id="color-picker",
            )

        if self._supports_color_temp():
            mireds = e.attributes.get("color_temp") or None
            min_m = e.attributes.get("min_mireds") or 153
            max_m = e.attributes.get("max_mireds") or 500
            kelvin = round(1_000_000 / mireds) if mireds else 4000
            min_k = round(1_000_000 / max_m)
            max_k = round(1_000_000 / min_m)
            yield Label("── COLOR TEMP ─────────", classes="section-divider")
            yield ColorTempPicker(
                initial_kelvin=float(kelvin),
                min_kelvin=min_k,
                max_kelvin=max_k,
                id="color-temp-picker",
            )

    def update_entity(self, entity: Entity) -> None:
        self._entity = entity
        is_on = entity.state == "on"

        self.query_one("#panel-status", Label).update(
            f">> {'ONLINE' if is_on else 'OFFLINE'}"
        )

        self._updating = True
        self.query_one("#light-switch", Switch).value = is_on
        self._updating = False

        b = entity.attributes.get("brightness") or 0
        try:
            self.query_one("#brightness-picker", BrightnessPicker).update_value(
                round(b / 255 * 100)
            )
        except Exception:
            pass

        hs = entity.attributes.get("hs_color")
        if hs:
            try:
                self.query_one("#color-picker", ColorPicker).update_hs(
                    float(hs[0]), float(hs[1])
                )
            except Exception:
                pass

        mireds = entity.attributes.get("color_temp")
        if mireds:
            try:
                self.query_one("#color-temp-picker", ColorTempPicker).update_kelvin(
                    round(1_000_000 / mireds)
                )
            except Exception:
                pass

    async def on_switch_changed(self, event: Switch.Changed) -> None:
        if self._updating:
            return
        service = "turn_on" if event.value else "turn_off"
        try:
            await self._client.call_service(
                "light", service, {"entity_id": self._entity.entity_id}
            )
            self.post_message(self.StateChanged())
        except Exception as exc:
            self.app.notify(_err(exc), severity="error")

    async def on_brightness_picker_applied(self, event: BrightnessPicker.Applied) -> None:
        try:
            await self._client.call_service(
                "light", "turn_on",
                {"entity_id": self._entity.entity_id, "brightness": round(event.brightness / 100 * 255)},
            )
            self.post_message(self.StateChanged())
        except Exception as exc:
            self.app.notify(_err(exc), severity="error")

    async def on_color_temp_picker_applied(self, event: ColorTempPicker.Applied) -> None:
        try:
            await self._client.call_service(
                "light", "turn_on",
                {"entity_id": self._entity.entity_id, "color_temp": round(1_000_000 / event.kelvin)},
            )
            self.post_message(self.StateChanged())
        except Exception as exc:
            self.app.notify(_err(exc), severity="error")

    async def on_color_picker_applied(self, event: ColorPicker.Applied) -> None:
        try:
            await self._client.call_service(
                "light", "turn_on",
                {"entity_id": self._entity.entity_id, "hs_color": [event.hue, event.saturation]},
            )
            self.post_message(self.StateChanged())
        except Exception as exc:
            self.app.notify(_err(exc), severity="error")


class ClimatePanel(Static):
    class StateChanged(Message):
        pass

    def __init__(self, entity: Entity, client: HAClient) -> None:
        super().__init__()
        self._entity = entity
        self._client = client

    def compose(self) -> ComposeResult:
        e = self._entity
        attrs = e.attributes
        current = attrs.get("current_temperature", "—")
        target = attrs.get("temperature") or attrs.get("target_temp_high") or "—"
        unit = attrs.get("temperature_unit", "")
        min_t = attrs.get("min_temp", 7)
        max_t = attrs.get("max_temp", 35)

        yield Label(f"// {e.name.upper()} //", id="panel-title")
        yield Label(f">> MODE: {e.state.upper()}", id="panel-status")
        yield Label(f"  CURRENT  {current}{unit}", id="label-current-temp", classes="temp-display")
        yield Label(f"  TARGET   {target}{unit}", id="label-target-temp", classes="temp-display")
        yield Label(f"  RANGE    {min_t}–{max_t}{unit}", classes="temp-range")
        with Horizontal(classes="control-row"):
            yield Label("SET TARGET", classes="control-label")
            yield Input(
                value=str(target) if target != "—" else "",
                id="temp-input",
                placeholder="Temperature",
            )
            yield Button("Set", id="btn-temp", variant="primary")

    def update_entity(self, entity: Entity) -> None:
        self._entity = entity
        attrs = entity.attributes
        current = attrs.get("current_temperature", "—")
        target = attrs.get("temperature") or attrs.get("target_temp_high") or "—"
        unit = attrs.get("temperature_unit", "")

        self.query_one("#panel-status", Label).update(f">> MODE: {entity.state.upper()}")
        self.query_one("#label-current-temp", Label).update(f"  CURRENT  {current}{unit}")
        self.query_one("#label-target-temp", Label).update(f"  TARGET   {target}{unit}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "btn-temp":
            return
        inp = self.query_one("#temp-input", Input)
        try:
            temp = float(inp.value)
            await self._client.call_service(
                "climate",
                "set_temperature",
                {"entity_id": self._entity.entity_id, "temperature": temp},
            )
            self.post_message(self.StateChanged())
        except ValueError:
            self.app.notify("Enter a valid temperature", severity="warning")
        except Exception as exc:
            self.app.notify(_err(exc), severity="error")


# ── Rooms tab widgets ──────────────────────────────────────────────────────

class NavLabel(Label):
    """A label that posts a Clicked message when the user clicks it."""

    class Clicked(Message):
        pass

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.post_message(self.Clicked())


class RoomLightRow(Horizontal):
    """A single light row inside a room card: clickable name + toggle switch."""

    class Toggled(Message):
        def __init__(self, entity_id: str, value: bool) -> None:
            self.entity_id = entity_id
            self.value = value
            super().__init__()

    class Navigate(Message):
        def __init__(self, entity_id: str) -> None:
            self.entity_id = entity_id
            super().__init__()

    def __init__(self, entity: Entity) -> None:
        super().__init__(classes="room-light-row")
        self._entity = entity
        self._updating = False

    def compose(self) -> ComposeResult:
        yield NavLabel(f"▸ {self._entity.name}", classes="room-light-name")
        yield Switch(value=self._entity.state == "on")

    def on_nav_label_clicked(self, _: NavLabel.Clicked) -> None:
        self.post_message(self.Navigate(self._entity.entity_id))

    def on_switch_changed(self, event: Switch.Changed) -> None:
        event.stop()
        if not self._updating:
            self.post_message(self.Toggled(self._entity.entity_id, event.value))

    def update_entity(self, entity: Entity) -> None:
        self._entity = entity
        self._updating = True
        self.query_one(Switch).value = entity.state == "on"
        self._updating = False
        try:
            self.query_one(".room-light-name", Label).update(f"▸ {entity.name}")
        except Exception:
            pass


class RoomCard(Static):
    """Card showing all lights in a single area with individual toggles and bulk controls."""

    def __init__(self, area: str, entities: list[Entity], client: HAClient) -> None:
        super().__init__(classes="room-card")
        self._area = area
        self._lights = sorted(
            (e for e in entities if e.domain == "light"), key=lambda e: e.name
        )
        self._client = client

    def _summary(self) -> str:
        on = sum(1 for e in self._lights if e.state == "on")
        return f"── {self._area.upper()} ──  {on}/{len(self._lights)} on"

    def compose(self) -> ComposeResult:
        yield Label(self._summary(), classes="room-card-header")
        for entity in self._lights:
            yield RoomLightRow(entity)
        with Horizontal(classes="room-card-buttons"):
            yield Button("All On", id="btn-all-on")
            yield Button("All Off", id="btn-all-off")

    def update_lights(self, entities: list[Entity]) -> None:
        self._lights = sorted(
            (e for e in entities if e.domain == "light"), key=lambda e: e.name
        )
        try:
            self.query_one(".room-card-header", Label).update(self._summary())
        except Exception:
            pass
        entity_map = {e.entity_id: e for e in self._lights}
        for row in self.query(RoomLightRow):
            if row._entity.entity_id in entity_map:
                row.update_entity(entity_map[row._entity.entity_id])

    async def on_room_light_row_toggled(self, event: RoomLightRow.Toggled) -> None:
        service = "turn_on" if event.value else "turn_off"
        try:
            await self._client.call_service("light", service, {"entity_id": event.entity_id})
            self.app.set_timer(0.5, self.app.refresh_entities)
        except Exception as exc:
            self.app.notify(_err(exc), severity="error")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id not in ("btn-all-on", "btn-all-off"):
            return
        event.stop()
        service = "turn_on" if event.button.id == "btn-all-on" else "turn_off"
        ids = [e.entity_id for e in self._lights]
        try:
            await self._client.call_service("light", service, {"entity_id": ids})
            self.app.set_timer(0.5, self.app.refresh_entities)
        except Exception as exc:
            self.app.notify(_err(exc), severity="error")


class RoomsView(ScrollableContainer):
    """Full-width scrollable overview of all rooms."""

    def __init__(self, client: HAClient) -> None:
        super().__init__(id="rooms-view")
        self._client = client

    @staticmethod
    def _group(entities: list[Entity], area_map: dict[str, str]) -> dict[str, list[Entity]]:
        groups: dict[str, list[Entity]] = defaultdict(list)
        for e in entities:
            if e.domain != "light":
                continue
            area = area_map.get(e.entity_id) or "Uncategorized"
            groups[area].append(e)
        areas = sorted(k for k in groups if k != "Uncategorized")
        if "Uncategorized" in groups:
            areas.append("Uncategorized")
        return {a: groups[a] for a in areas}

    async def update_rooms(self, entities: list[Entity], area_map: dict[str, str]) -> None:
        new_groups = self._group(entities, area_map)
        existing = {card._area: card for card in self.query(RoomCard)}
        if set(existing) == set(new_groups):
            for area, card in existing.items():
                card.update_lights(new_groups[area])
        else:
            await self.remove_children()
            for area, lights in new_groups.items():
                await self.mount(RoomCard(area, lights, self._client))


# ── Scenes tab widgets ─────────────────────────────────────────────────────

class SceneRow(Horizontal):
    """A single scene row: name + Activate button."""

    def __init__(self, entity: Entity, client: HAClient) -> None:
        super().__init__(classes="scene-row")
        self._entity = entity
        self._client = client

    def compose(self) -> ComposeResult:
        yield Label(self._entity.name, classes="scene-name")
        yield Button("Activate", id="btn-activate")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-activate":
            event.stop()
            try:
                await self._client.call_service(
                    "scene", "turn_on", {"entity_id": self._entity.entity_id}
                )
                self.app.notify(f"'{self._entity.name}' activated", timeout=3)
            except Exception as exc:
                self.app.notify(_err(exc), severity="error")


class ScenesView(ScrollableContainer):
    """Full-width list of all scenes with Activate buttons."""

    def __init__(self, client: HAClient) -> None:
        super().__init__(id="scenes-view")
        self._client = client
        self._scene_ids: list[str] = []

    async def update_scenes(self, scenes: list[Entity]) -> None:
        new_ids = [s.entity_id for s in scenes]
        if new_ids == self._scene_ids:
            return
        self._scene_ids = new_ids
        await self.remove_children()
        if not scenes:
            await self.mount(Label("> NO SCENES FOUND_", classes="scenes-empty"))
            return
        await self.mount(Label("── SCENES ──────────────────", classes="scenes-header"))
        for scene in scenes:
            await self.mount(SceneRow(scene, self._client))


# ── Main app ───────────────────────────────────────────────────────────────

class HATuiApp(App[None]):
    CSS_PATH = "app.tcss"
    TITLE = "HA-CTRL"
    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("s", "settings", "Settings"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, config: Config) -> None:
        self._active_theme = getattr(config, "theme", DEFAULT_THEME)
        super().__init__()
        self._config = config
        self._client = HAClient(config.url, config.token)
        self._entities: list[Entity] = []
        self._scenes: list[Entity] = []
        self._area_map: dict[str, str] = {}
        self._selected_id: str | None = None

    def get_css_variables(self) -> dict[str, str]:
        theme_vars = THEMES.get(getattr(self, "_active_theme", DEFAULT_THEME), THEMES[DEFAULT_THEME])
        scrollbar_vars = {
            "scrollbar":                    theme_vars["ha-border-dim"],
            "scrollbar-hover":              theme_vars["ha-primary"],
            "scrollbar-active":             theme_vars["ha-primary"],
            "scrollbar-background":         theme_vars["ha-surface"],
            "scrollbar-background-hover":   theme_vars["ha-surface"],
            "scrollbar-background-active":  theme_vars["ha-surface"],
            "scrollbar-corner-color":       theme_vars["ha-surface"],
        }
        return {**super().get_css_variables(), **theme_vars, **scrollbar_vars}

    def _apply_theme(self, theme_name: str) -> None:
        self._active_theme = theme_name
        self.refresh_css()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="tab-bar"):
            yield Tabs(
                Tab("DEVICES", id="tab-devices"),
                Tab("ROOMS", id="tab-rooms"),
                Tab("SCENES", id="tab-scenes"),
                id="main-tabs",
            )
            yield Button("⚙", id="btn-settings")
        with ContentSwitcher(initial="pane-devices", id="content-switcher"):
            with Container(id="pane-devices"):
                with Horizontal(id="body"):
                    with Container(id="sidebar"):
                        yield ListView(id="entity-list")
                    with ScrollableContainer(id="detail"):
                        yield Label("> SELECT NODE_", id="placeholder")
            with Container(id="pane-rooms"):
                yield RoomsView(self._client)
            with Container(id="pane-scenes"):
                yield ScenesView(self._client)
        yield Footer()

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        if event.tab is None:
            return
        pane_map = {
            "tab-devices": "pane-devices",
            "tab-rooms":   "pane-rooms",
            "tab-scenes":  "pane-scenes",
        }
        pane_id = pane_map.get(event.tab.id)
        if pane_id:
            self.query_one(ContentSwitcher).current = pane_id

    def on_mount(self) -> None:
        self.refresh_entities()
        self.set_interval(30, self.refresh_entities)

    @work(exclusive=True)
    async def refresh_entities(self) -> None:
        try:
            self._entities = await self._client.get_states()
        except Exception as exc:
            self.notify(f"Connection failed: {_err(exc)}", severity="error", timeout=6)
            return
        try:
            self._area_map = await self._client.get_area_map()
        except Exception:
            self._area_map = {}
        try:
            self._scenes = await self._client.get_scenes()
        except Exception:
            self._scenes = []

        await self._rebuild_list()
        try:
            await self.query_one(RoomsView).update_rooms(self._entities, self._area_map)
        except Exception:
            pass
        try:
            await self.query_one(ScenesView).update_scenes(self._scenes)
        except Exception:
            pass
        if self._selected_id:
            entity = self._find(self._selected_id)
            if entity:
                await self._show_panel(entity)

    def _ordered_entities(self) -> list[tuple[str, Entity]]:
        """Return [(area_name, entity), ...] sorted by area then entity name."""
        groups: dict[str, list[Entity]] = defaultdict(list)
        for entity in self._entities:
            area = self._area_map.get(entity.entity_id) or "Uncategorized"
            groups[area].append(entity)

        areas = sorted(k for k in groups if k != "Uncategorized")
        if "Uncategorized" in groups:
            areas.append("Uncategorized")

        return [
            (area, entity)
            for area in areas
            for entity in sorted(groups[area], key=lambda e: e.name)
        ]

    async def _rebuild_list(self) -> None:
        lv = self.query_one("#entity-list", ListView)
        ordered = self._ordered_entities()
        new_ids = [e.entity_id for _, e in ordered]

        current_items = list(lv.query(EntityItem))
        if [item.entity.entity_id for item in current_items] == new_ids:
            for item, (_, entity) in zip(current_items, ordered):
                item.entity = entity
                item.query_one(".item-state", Label).update(_entity_state_str(entity))
            return

        await lv.clear()
        current_area: str | None = None
        for area, entity in ordered:
            if area != current_area:
                await lv.append(AreaHeader(area))
                current_area = area
            await lv.append(EntityItem(entity))

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, EntityItem):
            self._selected_id = event.item.entity.entity_id
            await self._show_panel(event.item.entity)

    async def _show_panel(self, entity: Entity) -> None:
        detail = self.query_one("#detail", ScrollableContainer)

        if entity.domain == "light":
            panels = list(detail.query(LightPanel))
            if panels and panels[0]._entity.entity_id == entity.entity_id:
                panels[0].update_entity(entity)
                return
        elif entity.domain == "climate":
            panels = list(detail.query(ClimatePanel))
            if panels and panels[0]._entity.entity_id == entity.entity_id:
                panels[0].update_entity(entity)
                return

        await detail.remove_children()
        if entity.domain == "light":
            await detail.mount(LightPanel(entity, self._client))
        elif entity.domain == "climate":
            await detail.mount(ClimatePanel(entity, self._client))

    def _find(self, entity_id: str) -> Entity | None:
        return next((e for e in self._entities if e.entity_id == entity_id), None)

    def on_light_panel_state_changed(self, _: LightPanel.StateChanged) -> None:
        self.set_timer(0.5, self.refresh_entities)

    def on_climate_panel_state_changed(self, _: ClimatePanel.StateChanged) -> None:
        self.set_timer(0.5, self.refresh_entities)

    async def on_room_light_row_navigate(self, event: RoomLightRow.Navigate) -> None:
        """Switch to the Devices tab and select the entity in the sidebar."""
        self.query_one("#main-tabs", Tabs).active = "tab-devices"
        lv = self.query_one("#entity-list", ListView)
        for i, item in enumerate(lv.children):
            if isinstance(item, EntityItem) and item.entity.entity_id == event.entity_id:
                lv.index = i
                self._selected_id = event.entity_id
                await self._show_panel(item.entity)
                break

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-settings":
            self.action_settings()

    def action_refresh(self) -> None:
        self.refresh_entities()
        self.notify("Refreshing…", timeout=2)

    def action_settings(self) -> None:
        original_theme = self._active_theme

        def on_close(result: tuple[str, str, str] | None) -> None:
            if result is None:
                self._apply_theme(original_theme)
                return
            url, token, theme = result
            connection_changed = (url != self._config.url or token != self._config.token)
            self._config.url = url
            self._config.token = token
            self._config.theme = theme
            self._config.save()
            self._apply_theme(theme)
            if connection_changed:
                self._client = HAClient(url, token)
                self.refresh_entities()

        self.push_screen(SettingsScreen(self._config), callback=on_close)
