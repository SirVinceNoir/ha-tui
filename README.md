# ha-tui

A cyberpunk-themed Linux terminal UI for controlling [Home Assistant](https://www.home-assistant.io/).

```
┌─────────────────────────────────────────────────────────────────┐
│                        // HA-CTRL //                            │
├──────────────────┬──────────────────────────────────────────────┤
│ ── LIVING ROOM ──│ // LIVING ROOM LIGHTS //                     │
│ > Corner Lamp    │ >> ONLINE                                     │
│   ONLINE  80%    │                                               │
│ > Living Room    │ PWR  [■ on]                                   │
│   ONLINE  60%    │                                               │
│ ── KITCHEN ──    │ LUX  [░░░░░░░░░░░░░▲████████████████████]    │
│ > Kitchen Lights │      [80        ] [Set]                       │
│   OFFLINE        │                                               │
│ ── BEDROOM ──    │ ── COLOR TEMP ─────────                       │
│ > Bedroom Lights │ TEMP [████████████▲░░░░░░░░░░░░░░░░░░░░░░░]  │
│   ONLINE  40%    │      [████████████████████████████████████]   │
│                  │      [Apply Temp]                             │
└──────────────────┴──────────────────────────────────────────────┘
```

## Features

- **Lights** — toggle on/off, adjust brightness, set RGB colour and colour temperature via interactive gradient sliders
- **Climate** — view current temperature, mode, and set a target temperature
- **Rooms** — sidebar automatically organised by your Home Assistant areas
- **Interactive sliders** — click anywhere on a gradient bar or use ←/→ arrow keys to scrub; colour preview updates live
- **No flash** — state updates happen in-place so the UI doesn't flicker on every poll
- **Auto-refresh** — polls Home Assistant every 30 seconds; also refreshes 0.5s after any action

## Requirements

- Python 3.10+
- A local Home Assistant instance
- A [long-lived access token](https://developers.home-assistant.io/docs/auth_api/#long-lived-access-token)

## Installation

```bash
git clone https://github.com/SirVinceNoir/ha-tui.git
cd ha-tui
python -m venv .venv
.venv/bin/pip install -e .
```

## Configuration

On first run you will be prompted for your Home Assistant URL and access token. These are saved to `~/.config/ha-tui/config.toml`.

To generate a token: open Home Assistant → your profile → **Long-Lived Access Tokens** → **Create Token**.

You can also create the config file manually:

```toml
# ~/.config/ha-tui/config.toml
url = "http://192.168.1.x:8123"
token = "your-token-here"
```

## Usage

```bash
cd ha-tui
.venv/bin/ha-tui
```

### Key bindings

| Key | Action |
|-----|--------|
| `r` | Manual refresh |
| `q` | Quit |
| `tab` | Move focus between controls |
| `←` / `→` | Scrub a focused slider |

### Light controls

| Control | Description |
|---------|-------------|
| PWR switch | Toggle on/off |
| LUX slider | Brightness (0–100%) |
| HUE / SAT sliders | RGB colour (on supported lights) |
| TEMP slider | Colour temperature in Kelvin (on supported lights) |

## Project structure

```
ha_tui/
  app.py       # Textual TUI — layout, panels, event handling
  widgets.py   # Reusable slider widgets (brightness, hue/sat, colour temp)
  client.py    # Home Assistant REST API client
  config.py    # Config file handling
  app.tcss     # Cyberpunk CSS theme
  main.py      # Entry point / first-run setup
```
