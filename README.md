# ha-tui

A Linux terminal UI for controlling [Home Assistant](https://www.home-assistant.io/), with multiple themes and interactive gradient sliders.

```
┌─────────────────────────────────────────────────────────────────────┐
│  HA-CTRL                                               (clock)      │
├──────────────────────────────────────────────────────────────────── │
│  DEVICES       ROOMS       SCENES                               ⚙   │
├──────────────────┬──────────────────────────────────────────────────┤
│ ── LIVING ROOM ──│ // LIVING ROOM LIGHTS //                         │
│ > Corner Lamp    │ >> ONLINE                                        │
│   ONLINE  80%    │                                                  │
│ > Living Room    │ PWR  [■ on]                                      │
│   ONLINE  60%    │                                                  │
│ ── KITCHEN ──    │ LUX  [░░░░░░░░░░░░░▲████████████████████]        │
│ > Kitchen Lights │      [80        ] [Set]                          │
│   OFFLINE        │                                                  │
│ ── BEDROOM ──    │ ── COLOR TEMP ─────────                          │
│ > Bedroom Lights │ TEMP [████████████▲░░░░░░░░░░░░░░░░░░░░░░░]     │
│   ONLINE  40%    │      [████████████████████████████████████]      │
│                  │      [Apply Temp]                                │
└──────────────────┴──────────────────────────────────────────────────┘
```

## Features

- **Lights** — toggle on/off, adjust brightness, set RGB colour and colour temperature via interactive gradient sliders
- **Climate** — view current temperature, mode, and set a target temperature
- **Rooms tab** — overview of every area with individual light toggles and All On / All Off buttons per room; click a light name to jump to its detail in the Devices tab
- **Scenes tab** — list all Home Assistant scenes with one-click activation
- **Devices tab** — sidebar automatically organised by your Home Assistant areas; select an entity to see full controls in the detail panel
- **Interactive sliders** — click anywhere on a gradient bar or use ←/→ arrow keys to scrub; colour preview updates live
- **Themes** — five built-in themes (Cyberpunk, Matrix, Amber, Nord, Blood Moon) with live preview when switching; selected theme persists across restarts
- **Settings screen** — change your HA connection or theme without leaving the TUI (⚙ button on the right of the tab bar, or `s`); connection is tested before saving so invalid credentials are caught immediately
- **No flash** — state updates happen in-place so the UI doesn't flicker on every poll
- **Auto-refresh** — polls Home Assistant every 30 seconds; also refreshes 0.5s after any action

## Requirements

- Python 3.10+
- A local Home Assistant instance
- A [long-lived access token](https://developers.home-assistant.io/docs/auth_api/#long-lived-access-token)
- A terminal with 24-bit true colour support (most modern terminals: Kitty, Alacritty, WezTerm, GNOME Terminal, etc.)

## Installation & setup

### 1. Clone the repo

```bash
git clone https://github.com/SirVinceNoir/ha-tui.git
cd ha-tui
```

### 2. Create a virtual environment and install

```bash
python -m venv .venv
.venv/bin/pip install -e .
```

### 3. Generate a Home Assistant token

1. Open Home Assistant in your browser
2. Click your profile picture (bottom-left)
3. Scroll to **Long-Lived Access Tokens** → **Create Token**
4. Give it a name (e.g. `ha-tui`) and copy the token — you won't see it again

### 4. Run for the first time

```bash
.venv/bin/ha-tui
```

You'll be prompted for your Home Assistant URL (e.g. `http://192.168.1.x:8123`) and the token you just copied. These are saved to `~/.config/ha-tui/config.toml` and can be changed later from the in-app settings screen (`s` or ⚙).

### Optional: run from anywhere

To launch `ha-tui` without changing directory each time, add an alias to your shell config (`~/.bashrc` or `~/.zshrc`):

```bash
alias ha-tui='/path/to/ha-tui/.venv/bin/ha-tui'
```

Or create a symlink into a directory on your `$PATH`:

```bash
ln -s /path/to/ha-tui/.venv/bin/ha-tui ~/.local/bin/ha-tui
```

## Configuration

Config is stored at `~/.config/ha-tui/config.toml` and can be edited manually or via the in-app settings screen:

```toml
url = "http://192.168.1.x:8123"
token = "your-token-here"
theme = "cyberpunk"
```

## Usage

```bash
ha-tui
```

### Key bindings

| Key | Action |
|-----|--------|
| `s` or `⚙` | Open settings |
| `r` | Manual refresh |
| `q` | Quit |
| `tab` | Move focus between controls |
| `←` / `→` | Scrub a focused slider |

### Tabs

| Tab | Description |
|-----|-------------|
| DEVICES | Sidebar entity list + full detail panel (sliders, colour pickers, climate controls) |
| ROOMS | Room cards — individual light toggles, bulk All On/Off; click a light name to open it in the Devices tab |
| SCENES | All HA scenes with an Activate button for each |

### Light controls (Devices tab)

| Control | Description |
|---------|-------------|
| PWR switch | Toggle on/off |
| LUX slider | Brightness (0–100%) |
| HUE / SAT sliders | RGB colour (on supported lights) |
| TEMP slider | Colour temperature in Kelvin (on supported lights) |

### Themes

| Theme | Description |
|-------|-------------|
| Cyberpunk | Neon cyan and magenta on near-black |
| Matrix | Neon green on black |
| Amber | Amber and orange on dark brown — retro terminal feel |
| Nord | Soft blue-grey palette |
| Blood Moon | Deep red on black |

Themes can be switched live from the settings screen (`s` or ⚙) with an instant preview before saving.

## Project structure

```
ha_tui/
  app.py       # Textual TUI — layout, panels, event handling
  widgets.py   # Reusable slider widgets (brightness, hue/sat, colour temp)
  client.py    # Home Assistant REST API client
  config.py    # Config file handling
  themes.py    # Theme definitions
  settings.py  # Settings modal screen
  app.tcss     # CSS layout and theming
  main.py      # Entry point / first-run setup
```
