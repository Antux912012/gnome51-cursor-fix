# Technical Reference (ASD-STE100)

This document explains how `gnome51-cursor-fix.py` works and how to troubleshoot issues.

## 1. Cause of the Problem

1. GNOME Shell 51 introduces `StCursor` in `libst`.
2. `StCursor` searches `<theme>/cursors_scalable/<cursor-name>/metadata.json`.
3. Legacy cursor themes only provide Xcursor binary files in `<theme>/cursors/`.
4. When `StCursor` does not find `metadata.json`, it fails to load the cursor sprite.
5. As a result, the cursor icon stays on the initial arrow and does not change.

## 2. How the Script Fixes the Problem

For each cursor theme with a `cursors/` directory, the script performs these steps:

1. If `~/.icons` does not exist and `--no-symlink-icons` is not set, it creates a symlink from `~/.icons` to `~/.local/share/icons`.
2. If `index.theme` exists and has no `Inherits=` line, it appends `Inherits=Adwaita` (unless `--no-inherits` is set).
3. It creates `cursors_scalable/` inside the real theme directory.
4. For each regular Xcursor file in `cursors/`:
   - It reads the Xcursor header and table of contents.
   - It selects one nominal size according to `--size-strategy`.
   - It converts each frame from premultiplied BGRA pixels to RGBA PNG data.
   - It embeds the PNG data inside an SVG file.
   - It writes `metadata.json` with the filename, hotspot coordinates, nominal size, and frame delay (for animated cursors).
5. For each symlink in `cursors/`, it creates the matching symlink in `cursors_scalable/`.

## 3. Output Directory Structure

Each converted cursor theme has this structure:

```text
<theme>/
├── cursors/
├── index.theme
└── cursors_scalable/
    ├── default/
    │   ├── default.svg
    │   └── metadata.json
    ├── wait/
    │   ├── wait-01.svg
    │   ├── wait-02.svg
    │   └── metadata.json
    └── e-resize -> size_hor
```

## 4. `metadata.json` Format

For a static cursor, `metadata.json` contains one object:

```json
[
    {
        "filename": "default.svg",
        "hotspot_x": 8,
        "hotspot_y": 8,
        "nominal_size": 48
    }
]
```

For an animated cursor, `metadata.json` contains one object per frame, with `delay` in milliseconds:

```json
[
    {
        "filename": "wait-01.svg",
        "hotspot_x": 16,
        "hotspot_y": 16,
        "nominal_size": 48,
        "delay": 50
    }
]
```

## 5. Size Selection Strategy

Xcursor files often store multiple resolutions (for example: `24`, `30`, `36`, `48`). Use `--size-strategy` to choose which resolution to extract:

- `largest` (default): Extracts the highest available resolution. GNOME Shell scales it to your configured `cursor-size` using `nominal_size`.
- `smallest`: Extracts the lowest available resolution.
- `closest:<px>`: Extracts the resolution closest to `<px>`. For example, `closest:24` selects `24`.

## 6. Exit Codes

| Code | Meaning |
| :--- | :--- |
| `0` | Success. All matching themes were processed. |
| `1` | No cursor themes with a `cursors/` directory were found. |
| `2` | Invalid CLI arguments. |

## 7. Troubleshooting

### The cursor still does not change after running the script

1. Log out and log in again. GNOME Shell caches cursor resources in the running session.
2. Check the user journal for cursor errors:

```bash
journalctl --user -b | grep -i "Could not load cursor"
```

3. Verify that your active theme has `cursors_scalable/`:

```bash
gsettings get org.gnome.desktop.interface cursor-theme
```

### Permission denied when using `--system`

System themes under `/usr/share/icons` are owned by `root`. Run the script with `sudo`:

```bash
sudo ./gnome51-cursor-fix.py --system
```

### Existing `cursors_scalable/` files are skipped

By default, the script skips cursors that already have `metadata.json`. Run with `--force` to overwrite them:

```bash
./gnome51-cursor-fix.py --force
```
