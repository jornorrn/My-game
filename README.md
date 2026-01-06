# MysticEcho

A fast-paced 2D roguelike survivor built with Pygame-CE. Collect weapons, level up, and survive scaling enemy waves on a procedurally generated forest map.

## Features
- Player & enemy systems: WASD movement, mouse-facing aiming, enemy pursuit with collision damage.
- Weapon system: projectile, orbital, and aura types; independent cooldowns; upgrade-driven stat changes.
- Upgrade system: data-driven options from `assets/json/upgrades.json` (stat buffs, new weapons, heals, specials).
- Map system: procedurally generated forest with walls, trees, and decorations; Y-sort camera with culling.
- UI & audio: custom HUD, menus (main/pause/death/level-up), tutorial overlay, SFX/BGM with mute toggle.
- Performance tweaks: view frustum culling, distance-based enemy update rate, VFX limits.

## Requirements
- Python 3.10+ (tested with Python 3.13.3)
- Pygame-CE 2.5+ (audio needed for SFX/BGM)

Install deps:
```bash
pip install pygame-ce
```

## How to Run
```bash
python main.py
```

## Controls
- Movement: `W/A/S/D`
- Pause/Resume: `Esc`
- Mouse: aim and interact with UI buttons (menus, level-up cards, sound toggle)

## Project Structure
- `main.py` — entrypoint, starts `Game`
- `src/game.py` — game loop, state machine, spawning, rendering
- `src/settings.py` — global constants (window, layers, spawn limits)
- `src/loader.py` — resource manager for graphics/audio/json
- `src/components.py` — core sprite/physics (Entity, Tile, Y-sort camera)
- `src/player.py` — player logic, input, XP/level, weapon controller
- `src/enemy.py` — enemy AI, animations, damage/death handling
- `src/weapon.py` — projectile/orbital/aura weapons, controller
- `src/map_manager.py` — procedural forest generation and instantiation
- `src/upgrade_system.py` — upgrade database & application
- `src/ui.py` — HUD, menus, cards, custom cursor
- `src/audio_manager.py` — BGM/SFX playback, mute toggle
- `src/vfx.py` — animation player, hit flashes, explosions
- `assets/graphics` — spritesheets, UI art
- `assets/audio` — `bgm/` and `sfx/`
- `assets/json` — `weapons.json`, `enemies.json`, `upgrades.json`

## Game States
- `MENU` → `TUTORIAL` → `PLAYING` → `LEVEL_UP` / `PAUSED` / `GAME_OVER`
- Audio follows state; mute toggle persists until changed.

## Troubleshooting
- No sound: ensure `pygame-ce` installed and audio device available.
- Black/blank screen: verify assets path intact and run from project root (`python main.py`).
- Low FPS with many enemies: limits are configurable in `src/settings.py` (`MAX_ENEMIES`, `MAX_VFX_COUNT`).
