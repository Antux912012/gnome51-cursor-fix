# gnome51-cursor-fix

This tool fixes cursor icons that do not change in GNOME 51.

## 1. Overview

In GNOME 51, GNOME Shell uses `StCursor` to show cursor icons. `StCursor` reads scalable SVG cursors from the `cursors_scalable/` directory in each theme. Legacy third-party cursor themes only contain Xcursor bitmap files in the `cursors/` directory. Because `cursors_scalable/` is missing, GNOME Shell cannot load the cursor and logs this error:

```text
gnome-shell: Could not load cursor 'default': No file found
gnome-shell: Could not load cursor 'text': No file found
gnome-shell: Could not load cursor 'pointer': No file found
```

In addition, `libXcursor` searches `~/.icons`, `/usr/share/icons`, and `/usr/share/pixmaps` by default. If `~/.icons` does not exist, `libXcursor` does not find themes in `~/.local/share/icons`.

This tool converts legacy Xcursor files into `cursors_scalable/` directories. It requires only Python 3 standard library modules.

## 2. Requirements

- Linux with GNOME 51 or later.
- Python 3.10 or later.
- Write access to the target icon directories.

## 3. Installation

1. Clone the repository:

```bash
git clone https://github.com/Antux912012/gnome51-cursor-fix.git
```

2. Open the project directory:

```bash
cd gnome51-cursor-fix
```

3. Make the script executable:

```bash
chmod +x gnome51-cursor-fix.py
```

## 4. Quick Start

1. Run the script for all user cursor themes:

```bash
./gnome51-cursor-fix.py
```

2. Log out of your GNOME session.
3. Log in again to reload GNOME Shell.

## 5. CLI Options

| Option | Short | Default | Description |
| :--- | :--- | :--- | :--- |
| `--icons-dir PATH` | `-d` | `~/.local/share/icons`, `~/.icons` | Scan this icon directory. You can repeat this option. |
| `--system` | — | Disabled | Also scan `/usr/share/icons`. Run with `sudo` if required. |
| `--theme NAME` | `-t` | All themes | Process only this theme name. You can repeat this option. |
| `--size-strategy STR` | — | `largest` | Select Xcursor size: `largest`, `smallest`, or `closest:<px>`. |
| `--add-inherits THEME` | — | `Adwaita` | Add `Inherits=<THEME>` to `index.theme` when missing. |
| `--no-inherits` | — | Disabled | Do not change `index.theme` files. |
| `--no-symlink-icons` | — | Disabled | Do not create the `~/.icons` symlink. |
| `--force` | `-f` | Disabled | Overwrite existing `cursors_scalable/` entries. |
| `--dry-run` | `-n` | Disabled | Show planned changes without writing files. |
| `--verbose` | `-v` | Disabled | Print details for each cursor. |
| `--version` | — | — | Show the program version and exit. |
| `--help` | `-h` | — | Show the help message and exit. |

## 6. Examples

### Preview changes for one theme

```bash
./gnome51-cursor-fix.py --theme Graphite-dark-cursors --dry-run --verbose
```

### Overwrite existing scalable cursors

```bash
./gnome51-cursor-fix.py --force
```

### Convert a theme to a target size

```bash
./gnome51-cursor-fix.py --size-strategy closest:32 --force
```

### Convert system-wide themes

```bash
sudo ./gnome51-cursor-fix.py --system
```

## 7. Detailed Documentation

Read [docs/REFERENCE.md](docs/REFERENCE.md) for full technical details, file formats, and troubleshooting steps.

## 8. License

This project uses the MIT License. Read [LICENSE](LICENSE) for details.
