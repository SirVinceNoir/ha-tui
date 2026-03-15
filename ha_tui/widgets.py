from __future__ import annotations

import colorsys
import math

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static


def _hs_to_hex(hue: float, sat: float, val: float = 1.0) -> str:
    """Convert HSV (hue 0-360, sat 0-100, val 0-1) to #rrggbb."""
    r, g, b = colorsys.hsv_to_rgb(hue / 360, sat / 100, val)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


class HueSlider(Widget):
    """A clickable full-spectrum hue gradient bar."""

    can_focus = True

    DEFAULT_CSS = """
    HueSlider { height: 1; width: 1fr; }
    HueSlider:focus { border: none; }
    """

    hue: reactive[float] = reactive(0.0, layout=False, repaint=True)

    class Changed(Message):
        def __init__(self, hue: float) -> None:
            self.hue = hue
            super().__init__()

    def __init__(self, initial_hue: float = 0.0, **kwargs) -> None:
        super().__init__(**kwargs)
        self.hue = initial_hue

    def render(self):
        from rich.text import Text

        width = max(1, self.size.width)
        text = Text(no_wrap=True, overflow="crop")
        cursor = round(self.hue / 360 * (width - 1)) if width > 1 else 0
        marker = "▼" if self.has_focus else "▲"
        for i in range(width):
            h = (i / (width - 1) * 360) if width > 1 else 0.0
            color = _hs_to_hex(h, 100)
            text.append(marker if i == cursor else "█", style=f"white on {color}" if i == cursor else color)
        return text

    def on_focus(self) -> None: self.refresh()
    def on_blur(self) -> None:  self.refresh()

    def on_click(self, event: events.Click) -> None:
        self.hue = max(0.0, min(360.0, event.x / max(1, self.size.width - 1) * 360))
        self.post_message(self.Changed(self.hue))

    def on_key(self, event: events.Key) -> None:
        if event.key == "left":
            self.hue = max(0.0, self.hue - 1)
            self.post_message(self.Changed(self.hue))
            event.stop()
        elif event.key == "right":
            self.hue = min(360.0, self.hue + 1)
            self.post_message(self.Changed(self.hue))
            event.stop()


class SatSlider(Widget):
    """A clickable saturation gradient bar (white → full hue colour)."""

    can_focus = True

    DEFAULT_CSS = """
    SatSlider { height: 1; width: 1fr; }
    SatSlider:focus { border: none; }
    """

    hue: reactive[float] = reactive(0.0, layout=False, repaint=True)
    saturation: reactive[float] = reactive(100.0, layout=False, repaint=True)

    class Changed(Message):
        def __init__(self, saturation: float) -> None:
            self.saturation = saturation
            super().__init__()

    def __init__(self, initial_hue: float = 0.0, initial_sat: float = 100.0, **kwargs) -> None:
        super().__init__(**kwargs)
        self.hue = initial_hue
        self.saturation = initial_sat

    def render(self):
        from rich.text import Text

        width = max(1, self.size.width)
        text = Text(no_wrap=True, overflow="crop")
        cursor = round(self.saturation / 100 * (width - 1)) if width > 1 else 0
        marker = "▼" if self.has_focus else "▲"
        for i in range(width):
            s = (i / (width - 1) * 100) if width > 1 else 100.0
            color = _hs_to_hex(self.hue, s)
            text.append(marker if i == cursor else "█", style=f"white on {color}" if i == cursor else color)
        return text

    def on_focus(self) -> None: self.refresh()
    def on_blur(self) -> None:  self.refresh()

    def on_click(self, event: events.Click) -> None:
        self.saturation = max(0.0, min(100.0, event.x / max(1, self.size.width - 1) * 100))
        self.post_message(self.Changed(self.saturation))

    def on_key(self, event: events.Key) -> None:
        if event.key == "left":
            self.saturation = max(0.0, self.saturation - 1)
            self.post_message(self.Changed(self.saturation))
            event.stop()
        elif event.key == "right":
            self.saturation = min(100.0, self.saturation + 1)
            self.post_message(self.Changed(self.saturation))
            event.stop()


class ColorPreview(Widget):
    """A solid swatch showing the currently selected colour."""

    DEFAULT_CSS = """
    ColorPreview {
        height: 2;
        width: 1fr;
    }
    """

    hue: reactive[float] = reactive(0.0, layout=False, repaint=True)
    saturation: reactive[float] = reactive(100.0, layout=False, repaint=True)

    def render(self):
        from rich.text import Text

        color = _hs_to_hex(self.hue, self.saturation)
        return Text("█" * self.size.width * self.size.height, style=color)


class ColorPicker(Static):
    """Hue + saturation sliders with a live colour preview and apply button."""

    class Applied(Message):
        def __init__(self, hue: float, saturation: float) -> None:
            self.hue = hue
            self.saturation = saturation
            super().__init__()

    def __init__(self, initial_hue: float = 0.0, initial_sat: float = 100.0, **kwargs) -> None:
        super().__init__(**kwargs)
        self._initial_hue = initial_hue
        self._initial_sat = initial_sat

    def compose(self) -> ComposeResult:
        with Horizontal(classes="slider-row"):
            yield Label("HUE", classes="slider-label")
            yield HueSlider(initial_hue=self._initial_hue, id="hue-slider")
        with Horizontal(classes="slider-row"):
            yield Label("SAT", classes="slider-label")
            yield SatSlider(
                initial_hue=self._initial_hue,
                initial_sat=self._initial_sat,
                id="sat-slider",
            )
        with Horizontal(classes="slider-row"):
            yield Label("", classes="slider-label")
            yield ColorPreview(id="color-preview")
        yield Button("Apply Color", id="btn-apply-color", variant="primary")

    def on_hue_slider_changed(self, event: HueSlider.Changed) -> None:
        self.query_one("#sat-slider", SatSlider).hue = event.hue
        self.query_one("#color-preview", ColorPreview).hue = event.hue

    def on_sat_slider_changed(self, event: SatSlider.Changed) -> None:
        self.query_one("#color-preview", ColorPreview).saturation = event.saturation

    def update_hs(self, hue: float, sat: float) -> None:
        self.query_one("#hue-slider", HueSlider).hue = hue
        sat_slider = self.query_one("#sat-slider", SatSlider)
        sat_slider.hue = hue
        sat_slider.saturation = sat
        preview = self.query_one("#color-preview", ColorPreview)
        preview.hue = hue
        preview.saturation = sat

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-apply-color":
            hue = self.query_one("#hue-slider", HueSlider).hue
            sat = self.query_one("#sat-slider", SatSlider).saturation
            self.post_message(self.Applied(hue, sat))
            event.stop()


class BrightnessSlider(Widget):
    """A clickable brightness gradient bar (black → white)."""

    can_focus = True

    DEFAULT_CSS = """
    BrightnessSlider { height: 1; width: 1fr; }
    BrightnessSlider:focus { border: none; }
    """

    brightness: reactive[float] = reactive(100.0, layout=False, repaint=True)

    class Changed(Message):
        def __init__(self, brightness: float) -> None:
            self.brightness = brightness
            super().__init__()

    def __init__(self, initial_brightness: float = 100.0, **kwargs) -> None:
        super().__init__(**kwargs)
        self.brightness = initial_brightness

    def render(self):
        from rich.text import Text

        width = max(1, self.size.width)
        text = Text(no_wrap=True, overflow="crop")
        cursor = round(self.brightness / 100 * (width - 1)) if width > 1 else 0
        marker = "▼" if self.has_focus else "▲"
        for i in range(width):
            v = int(i / (width - 1) * 255) if width > 1 else 255
            color = f"#{v:02x}{v:02x}{v:02x}"
            if i == cursor:
                fg = "black" if v > 127 else "white"
                text.append(marker, style=f"{fg} on {color}")
            else:
                text.append("█", style=color)
        return text

    def on_focus(self) -> None: self.refresh()
    def on_blur(self) -> None:  self.refresh()

    def on_click(self, event: events.Click) -> None:
        self.brightness = max(0.0, min(100.0, event.x / max(1, self.size.width - 1) * 100))
        self.post_message(self.Changed(self.brightness))

    def on_key(self, event: events.Key) -> None:
        if event.key == "left":
            self.brightness = max(0.0, self.brightness - 1)
            self.post_message(self.Changed(self.brightness))
            event.stop()
        elif event.key == "right":
            self.brightness = min(100.0, self.brightness + 1)
            self.post_message(self.Changed(self.brightness))
            event.stop()


class BrightnessPicker(Static):
    """Brightness slider and numeric input with apply button."""

    class Applied(Message):
        def __init__(self, brightness: float) -> None:
            self.brightness = brightness
            super().__init__()

    def __init__(self, initial_brightness: float = 100.0, **kwargs) -> None:
        super().__init__(**kwargs)
        self._initial = initial_brightness

    def compose(self) -> ComposeResult:
        with Horizontal(classes="slider-row"):
            yield Label("LUX", classes="slider-label")
            yield BrightnessSlider(initial_brightness=self._initial, id="brightness-slider")
        with Horizontal(classes="slider-row"):
            yield Label("", classes="slider-label")
            yield Input(
                value=str(round(self._initial)),
                id="brightness-input",
                placeholder="0–100",
            )
            yield Button("Set", id="btn-apply-brightness", variant="primary")

    def on_brightness_slider_changed(self, event: BrightnessSlider.Changed) -> None:
        self.query_one("#brightness-input", Input).value = str(round(event.brightness))

    def update_value(self, pct: float) -> None:
        self.query_one("#brightness-slider", BrightnessSlider).brightness = pct
        self.query_one("#brightness-input", Input).value = str(round(pct))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "btn-apply-brightness":
            return
        inp = self.query_one("#brightness-input", Input)
        try:
            pct = max(0, min(100, int(inp.value)))
            # Sync slider to manually typed value
            self.query_one("#brightness-slider", BrightnessSlider).brightness = float(pct)
            self.post_message(self.Applied(float(pct)))
        except ValueError:
            self.app.notify("Enter a number between 0 and 100", severity="warning")
        event.stop()


def _kelvin_to_hex(kelvin: float) -> str:
    """Approximate conversion of a colour temperature in Kelvin to #rrggbb.

    Based on Tanner Helland's algorithm.
    """
    temp = max(1000.0, min(40000.0, kelvin)) / 100.0

    if temp <= 66:
        r = 255
        g = 99.4708025861 * math.log(temp) - 161.1195681661
        b = 0 if temp <= 19 else 138.5177312231 * math.log(temp - 10) - 305.0447927307
    else:
        r = 329.698727446 * ((temp - 60) ** -0.1332047592)
        g = 288.1221695283 * ((temp - 60) ** -0.0755148492)
        b = 255

    return (
        f"#{max(0, min(255, int(r))):02x}"
        f"{max(0, min(255, int(g))):02x}"
        f"{max(0, min(255, int(b))):02x}"
    )


class ColorTempSlider(Widget):
    """A clickable colour-temperature gradient bar (warm → cool)."""

    can_focus = True

    DEFAULT_CSS = """
    ColorTempSlider { height: 1; width: 1fr; }
    ColorTempSlider:focus { border: none; }
    """

    kelvin: reactive[float] = reactive(4000.0, layout=False, repaint=True)

    class Changed(Message):
        def __init__(self, kelvin: float) -> None:
            self.kelvin = kelvin
            super().__init__()

    def __init__(
        self,
        initial_kelvin: float = 4000.0,
        min_kelvin: int = 2000,
        max_kelvin: int = 6500,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.kelvin = initial_kelvin
        self._min_k = min_kelvin
        self._max_k = max_kelvin

    def render(self):
        from rich.text import Text

        width = max(1, self.size.width)
        k_range = self._max_k - self._min_k
        text = Text(no_wrap=True, overflow="crop")
        cursor = (
            round((self.kelvin - self._min_k) / k_range * (width - 1))
            if k_range and width > 1
            else 0
        )
        marker = "▼" if self.has_focus else "▲"
        for i in range(width):
            k = self._min_k + (i / (width - 1) * k_range) if width > 1 else float(self._min_k)
            color = _kelvin_to_hex(k)
            text.append(marker if i == cursor else "█", style=f"white on {color}" if i == cursor else color)
        return text

    def on_focus(self) -> None: self.refresh()
    def on_blur(self) -> None:  self.refresh()

    def on_click(self, event: events.Click) -> None:
        frac = event.x / max(1, self.size.width - 1)
        self.kelvin = max(
            float(self._min_k),
            min(float(self._max_k), self._min_k + frac * (self._max_k - self._min_k)),
        )
        self.post_message(self.Changed(self.kelvin))

    def on_key(self, event: events.Key) -> None:
        step = max(10.0, (self._max_k - self._min_k) / 100)
        if event.key == "left":
            self.kelvin = max(float(self._min_k), self.kelvin - step)
            self.post_message(self.Changed(self.kelvin))
            event.stop()
        elif event.key == "right":
            self.kelvin = min(float(self._max_k), self.kelvin + step)
            self.post_message(self.Changed(self.kelvin))
            event.stop()


class ColorTempPreview(Widget):
    """A solid swatch showing the current colour temperature."""

    DEFAULT_CSS = """
    ColorTempPreview {
        height: 2;
        width: 1fr;
    }
    """

    kelvin: reactive[float] = reactive(4000.0, layout=False, repaint=True)

    def __init__(self, initial_kelvin: float = 4000.0, **kwargs) -> None:
        super().__init__(**kwargs)
        self.kelvin = initial_kelvin

    def render(self):
        from rich.text import Text

        color = _kelvin_to_hex(self.kelvin)
        line = "█" * max(1, self.size.width)
        return Text("\n".join([line] * max(1, self.size.height)), style=color)


class ColorTempPicker(Static):
    """Colour temperature slider with live preview and apply button."""

    class Applied(Message):
        def __init__(self, kelvin: float) -> None:
            self.kelvin = kelvin
            super().__init__()

    def __init__(
        self,
        initial_kelvin: float = 4000.0,
        min_kelvin: int = 2000,
        max_kelvin: int = 6500,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._initial_k = initial_kelvin
        self._min_k = min_kelvin
        self._max_k = max_kelvin

    def compose(self) -> ComposeResult:
        with Horizontal(classes="slider-row"):
            yield Label("TEMP", classes="slider-label")
            yield ColorTempSlider(
                initial_kelvin=self._initial_k,
                min_kelvin=self._min_k,
                max_kelvin=self._max_k,
                id="ct-slider",
            )
        with Horizontal(classes="slider-row"):
            yield Label("", classes="slider-label")
            yield ColorTempPreview(initial_kelvin=self._initial_k, id="ct-preview")
        yield Button("Apply Temp", id="btn-apply-temp", variant="primary")

    def on_color_temp_slider_changed(self, event: ColorTempSlider.Changed) -> None:
        self.query_one("#ct-preview", ColorTempPreview).kelvin = event.kelvin

    def update_kelvin(self, kelvin: float) -> None:
        self.query_one("#ct-slider", ColorTempSlider).kelvin = kelvin
        self.query_one("#ct-preview", ColorTempPreview).kelvin = kelvin

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-apply-temp":
            kelvin = self.query_one("#ct-slider", ColorTempSlider).kelvin
            self.post_message(self.Applied(kelvin))
            event.stop()


def _temp_to_hex(temp: float, min_t: float, max_t: float) -> str:
    """Map a temperature in [min_t, max_t] to a blue→orange colour."""
    frac = max(0.0, min(1.0, (temp - min_t) / max(1.0, max_t - min_t)))
    hue = 220 - frac * 200  # 220° (cool blue) → 20° (warm orange)
    r, g, b = colorsys.hsv_to_rgb(hue / 360, 0.75, 1.0)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


class TempDisplay(Widget):
    """Shows current and target temperatures side by side with colour coding."""

    DEFAULT_CSS = """
    TempDisplay {
        height: 2;
        width: 100%;
        margin-bottom: 1;
    }
    """

    current: reactive = reactive("—", layout=False, repaint=True)
    target: reactive = reactive("—", layout=False, repaint=True)

    def __init__(
        self,
        current=None,
        target=None,
        unit: str = "",
        min_temp: float = 7.0,
        max_temp: float = 35.0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.current = current if current is not None else "—"
        self.target = target if target is not None else "—"
        self._unit = unit
        self._min = min_temp
        self._max = max_temp

    def _temp_color(self, temp) -> str:
        if not isinstance(temp, (int, float)):
            return "#888888"
        return _temp_to_hex(float(temp), self._min, self._max)

    def render(self):
        from rich.text import Text

        w = max(20, self.size.width)
        left_w = w * 2 // 5
        mid_w = max(3, w // 5)
        right_w = w - left_w - mid_w

        cur = self.current
        tgt = self.target
        cur_s = f"{cur}{self._unit}" if isinstance(cur, (int, float)) else str(cur)
        tgt_s = f"{tgt}{self._unit}" if isinstance(tgt, (int, float)) else str(tgt)

        t = Text(no_wrap=True, overflow="crop")
        t.append(f"{'CURRENT':^{left_w}}", style="dim")
        t.append(f"{'':^{mid_w}}")
        t.append(f"{'TARGET':^{right_w}}\n", style="dim")
        t.append(f"{cur_s:^{left_w}}", style=f"bold {self._temp_color(cur)}")
        t.append(f"{'→':^{mid_w}}", style="dim")
        t.append(f"{tgt_s:^{right_w}}", style=f"bold {self._temp_color(tgt)}")
        return t


class TempSlider(Widget):
    """Interactive temperature slider (blue→orange) showing current and target positions."""

    can_focus = True

    DEFAULT_CSS = """
    TempSlider { height: 1; width: 1fr; }
    TempSlider:focus { border: none; }
    """

    target: reactive[float] = reactive(20.0, layout=False, repaint=True)
    current: reactive[float] = reactive(20.0, layout=False, repaint=True)

    class Changed(Message):
        def __init__(self, temp: float) -> None:
            self.temp = temp
            super().__init__()

    def __init__(
        self,
        target: float = 20.0,
        current: float = 20.0,
        min_temp: float = 7.0,
        max_temp: float = 35.0,
        step: float = 0.5,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.target = target
        self.current = current
        self._min = min_temp
        self._max = max_temp
        self._step = step

    def _pos(self, temp: float, width: int) -> int:
        t_range = self._max - self._min
        if not t_range or width <= 1:
            return 0
        return round((temp - self._min) / t_range * (width - 1))

    def render(self):
        from rich.text import Text

        width = max(1, self.size.width)
        text = Text(no_wrap=True, overflow="crop")
        target_pos = self._pos(self.target, width)
        current_pos = self._pos(self.current, width)
        marker = "▼" if self.has_focus else "▲"

        for i in range(width):
            t = self._min + (i / (width - 1) * (self._max - self._min)) if width > 1 else self._min
            color = _temp_to_hex(t, self._min, self._max)
            if i == target_pos:
                text.append(marker, style=f"black on {color}")
            elif i == current_pos:
                text.append("●", style=f"white on {color}")
            else:
                text.append("█", style=color)
        return text

    def on_focus(self) -> None: self.refresh()
    def on_blur(self) -> None: self.refresh()

    def on_click(self, event: events.Click) -> None:
        t_range = self._max - self._min
        raw = self._min + event.x / max(1, self.size.width - 1) * t_range
        self.target = max(self._min, min(self._max, round(raw / self._step) * self._step))
        self.post_message(self.Changed(self.target))

    def on_key(self, event: events.Key) -> None:
        if event.key == "left":
            self.target = max(self._min, round((self.target - self._step) / self._step) * self._step)
            self.post_message(self.Changed(self.target))
            event.stop()
        elif event.key == "right":
            self.target = min(self._max, round((self.target + self._step) / self._step) * self._step)
            self.post_message(self.Changed(self.target))
            event.stop()
