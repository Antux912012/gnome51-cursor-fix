# gnome51-cursor-fix

Fix cursor icons not changing in **GNOME 51+** when using third-party Xcursor themes.

## Why this happens

GNOME Shell 51 introduces `StCursor` (`libst`), which loads scalable SVG cursors from `<theme>/cursors_scalable/<cursor>/metadata.json` instead of legacy Xcursor bitmap files (`cursors/`). Third-party cursor themes that only ship `cursors/` fail to load with:

```text
gnome-shell: Could not load cursor 'default': No file found
gnome-shell: Could not load cursor 'text': No file found
gnome-shell: Could not load cursor 'pointer': No file found
```

Additionally, `libXcursor` defaults to `~/.icons:/usr/share/icons:/usr/share/pixmaps`, so themes installed only in `~/.local/share/icons` are missed if `~/.icons` does not exist.

## What this script does

- Zero external dependencies (Python 3 standard library only).
- Converts legacy Xcursor files (`cursors/`) into GNOME 51 `cursors_scalable/` (`metadata.json` + SVG-wrapped PNGs, preserving animations, hotspots, nominal sizes, and symlinks).
- Adds `Inherits=Adwaita` to `index.theme` if missing.
- Creates `~/.icons -> ~/.local/share/icons` if `~/.icons` does not exist.

## Usage

```bash
chmod +x gnome51-cursor-fix.py
./gnome51-cursor-fix.py
```

Log out and back in (or toggle your cursor theme in Settings / GNOME Tweaks) to reload GNOME Shell.

### Options

```text
-d, --icons-dir PATH      Icon directory to scan (repeatable).
                          Default: ~/.local/share/icons and ~/.icons
    --system              Also scan /usr/share/icons (run with sudo if needed)
-t, --theme NAME          Only process the named cursor theme (repeatable)
    --size-strategy STR   Xcursor size to extract: largest (default), smallest, or closest:<px>
    --add-inherits THEME  Fallback theme for index.theme (default: Adwaita)
    --no-inherits         Do not modify index.theme
    --no-symlink-icons    Do not create ~/.icons -> ~/.local/share/icons
-f, --force               Overwrite existing cursors_scalable/ entries
-n, --dry-run             Preview changes without writing files
-v, --verbose             Print per-cursor details
    --version             Show version
```

### Examples

Preview changes for a single theme:

```bash
./gnome51-cursor-fix.py --theme Graphite-dark-cursors --dry-run --verbose
```

Regenerate all user themes, overwriting existing `cursors_scalable/` directories:

```bash
./gnome51-cursor-fix.py --force
```

Include system-wide themes under `/usr/share/icons`:

```bash
sudo ./gnome51-cursor-fix.py --system
```
