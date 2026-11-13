#!/usr/bin/env python3
"""Generate GNOME 51 `cursors_scalable/` directories from legacy Xcursor themes."""

import argparse
import base64
import json
import os
import struct
import sys
import zlib
from pathlib import Path

__version__ = "1.0.0"

XCURSOR_MAGIC = b"Xcur"
XCURSOR_IMAGE_TYPE = 0xFFFD0002

ASCII_LOGO = r"""
   |\
   | \     ___ _  _  ___  __  __ ___   ___ _
   |  \   / __| \| |/ _ \|  \/  | __| | __| |
   |   \ | (_ | .` | (_) | |\/| | _|  |__ \ |
   | |\ \ \___|_|\_|\___/|_|  |_|___| |___/_|
   |_| \_\   GNOME 51 CURSOR FIX  v1.0.0
""".strip("\n")


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """Build a single PNG chunk with length and CRC32."""
    chunk = chunk_type + data
    return (
        struct.pack(">I", len(data))
        + chunk
        + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
    )


def bgra_premul_to_png(width: int, height: int, raw_pixels: bytes) -> bytes:
    """Convert little-endian premultiplied ARGB32 (BGRA bytes) to RGBA PNG bytes."""
    rows = []
    stride = width * 4
    for y in range(height):
        row = bytearray([0])  # PNG filter type 0 (None)
        off = y * stride
        for _ in range(width):
            b, g, r, a = raw_pixels[off : off + 4]
            off += 4
            if a == 0:
                row.extend((0, 0, 0, 0))
            elif a == 255:
                row.extend((r, g, b, 255))
            else:
                r = min(255, (r * 255 + a // 2) // a)
                g = min(255, (g * 255 + a // 2) // a)
                b = min(255, (b * 255 + a // 2) // a)
                row.extend((r, g, b, a))
        rows.append(bytes(row))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", zlib.compress(b"".join(rows), 6))
        + png_chunk(b"IEND", b"")
    )


def parse_xcursor(path: Path) -> dict[int, list[tuple[int, int, int, int, int, bytes]]] | None:
    """Parse an Xcursor file and return image frames grouped by nominal size."""
    try:
        data = path.read_bytes()
    except OSError:
        return None

    if len(data) < 16 or data[:4] != XCURSOR_MAGIC:
        return None

    _, hdr, _, ntoc = struct.unpack("<4sIII", data[:16])
    by_size: dict[int, list[tuple[int, int, int, int, int, bytes]]] = {}
    pos = hdr
    for _ in range(ntoc):
        if pos + 12 > len(data):
            break
        ctype, subtype, cpos = struct.unpack("<III", data[pos : pos + 12])
        pos += 12
        if ctype != XCURSOR_IMAGE_TYPE or cpos + 36 > len(data):
            continue
        chdr, _, _, _, w, h, xhot, yhot, delay = struct.unpack(
            "<IIIIIIIII", data[cpos : cpos + 36]
        )
        px_start = cpos + chdr
        px_end = px_start + w * h * 4
        if px_end > len(data):
            continue
        by_size.setdefault(subtype, []).append(
            (w, h, xhot, yhot, delay, data[px_start:px_end])
        )

    return by_size or None


def select_size(sizes: list[int], strategy: str) -> int:
    """Select which nominal cursor size to extract according to strategy."""
    if strategy == "largest":
        return max(sizes)
    if strategy == "smallest":
        return min(sizes)
    if strategy.startswith("closest:"):
        target = int(strategy.split(":", 1)[1])
        return min(sizes, key=lambda s: (abs(s - target), -s))
    raise ValueError(f"Unsupported size strategy: {strategy}")


def make_svg(width: int, height: int, png_bytes: bytes) -> str:
    """Wrap PNG bytes in a standalone SVG document."""
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        f'  <image width="{width}" height="{height}" '
        f'href="data:image/png;base64,{b64}"/>\n'
        f"</svg>\n"
    )


def ensure_inherits(theme_dir: Path, fallback: str, dry_run: bool, verbose: bool) -> bool:
    """Add Inherits=<fallback> to index.theme if missing. Returns True if updated."""
    index_path = theme_dir / "index.theme"
    if not index_path.is_file():
        return False
    content = index_path.read_text(encoding="utf-8", errors="replace")
    if "Inherits=" in content:
        return False
    if verbose or dry_run:
        print(f"  [index.theme] add Inherits={fallback} -> {index_path}")
    if not dry_run:
        index_path.write_text(content.rstrip() + f"\nInherits={fallback}\n", encoding="utf-8")
    return True


def ensure_icons_symlink(dry_run: bool, verbose: bool) -> None:
    """Symlink ~/.icons -> ~/.local/share/icons if ~/.icons does not exist."""
    home = Path.home()
    dot_icons = home / ".icons"
    local_icons = home / ".local" / "share" / "icons"
    if dot_icons.exists() or dot_icons.is_symlink() or not local_icons.is_dir():
        return
    if verbose or dry_run:
        print(f"[symlink] {dot_icons} -> {local_icons}")
    if not dry_run:
        dot_icons.symlink_to(local_icons)


def process_theme(
    theme_dir: Path,
    size_strategy: str,
    inherits: str | None,
    force: bool,
    dry_run: bool,
    verbose: bool,
) -> tuple[int, int]:
    """Convert one cursor theme's cursors/ into cursors_scalable/."""
    cursors_dir = theme_dir / "cursors"
    scalable_dir = theme_dir / "cursors_scalable"

    if inherits:
        ensure_inherits(theme_dir, inherits, dry_run, verbose)

    if not dry_run:
        scalable_dir.mkdir(exist_ok=True)

    entries = sorted(cursors_dir.iterdir(), key=lambda p: p.name)
    files_done = 0
    links_done = 0

    for src in entries:
        if src.is_symlink() or not src.is_file():
            continue
        parsed = parse_xcursor(src)
        if not parsed:
            if verbose:
                print(f"  [skip] non-xcursor file: {src.name}")
            continue

        out_dir = scalable_dir / src.name
        meta_path = out_dir / "metadata.json"
        if meta_path.exists() and not force:
            if verbose:
                print(f"  [skip] exists: {out_dir}")
            continue

        nominal_size = select_size(list(parsed.keys()), size_strategy)
        frames = parsed[nominal_size]
        is_anim = len(frames) > 1

        if verbose:
            print(f"  [cursor] {src.name} ({len(frames)} frame(s), nominal={nominal_size})")

        if not dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)

        meta = []
        for idx, (w, h, xhot, yhot, delay, pixels) in enumerate(frames, 1):
            svg_name = f"{src.name}-{idx:02d}.svg" if is_anim else f"{src.name}.svg"
            if not dry_run:
                png_bytes = bgra_premul_to_png(w, h, pixels)
                (out_dir / svg_name).write_text(make_svg(w, h, png_bytes), encoding="utf-8")
            entry: dict[str, object] = {
                "filename": svg_name,
                "hotspot_x": xhot,
                "hotspot_y": yhot,
                "nominal_size": nominal_size,
            }
            if is_anim:
                entry["delay"] = delay
            meta.append(entry)

        if not dry_run:
            meta_path.write_text(json.dumps(meta, indent=4) + "\n", encoding="utf-8")
        files_done += 1

    for src in entries:
        if not src.is_symlink():
            continue
        target = os.readlink(src)
        dst = scalable_dir / src.name
        if dst.exists() or dst.is_symlink():
            if not force:
                continue
            if not dry_run and dst.is_symlink():
                dst.unlink()
            elif not dst.is_symlink():
                continue
        if verbose:
            print(f"  [link] {src.name} -> {target}")
        if not dry_run:
            dst.symlink_to(target)
        links_done += 1

    return files_done, links_done


def collect_themes(icons_dirs: list[Path], theme_filters: set[str]) -> list[tuple[str, Path]]:
    """Discover unique cursor themes across the given icon directories."""
    seen_real: set[Path] = set()
    themes: list[tuple[str, Path]] = []

    for base in icons_dirs:
        if not base.is_dir():
            continue
        for entry in sorted(base.iterdir(), key=lambda p: p.name):
            if theme_filters and entry.name not in theme_filters:
                continue
            real = entry.resolve()
            if real in seen_real:
                continue
            if (real / "cursors").is_dir():
                seen_real.add(real)
                themes.append((entry.name, real))
    return themes


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="gnome51-cursor-fix",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            f"{ASCII_LOGO}\n\n"
            "Fix cursor icons in GNOME 51 by generating cursors_scalable/ "
            "(SVG + metadata.json) from legacy Xcursor themes."
        ),
    )
    parser.add_argument(
        "-d",
        "--icons-dir",
        action="append",
        type=Path,
        default=None,
        help="Icon directory to scan (repeatable). Default: ~/.local/share/icons and ~/.icons",
    )
    parser.add_argument(
        "--system",
        action="store_true",
        help="Also scan /usr/share/icons (requires write permissions, e.g. sudo).",
    )
    parser.add_argument(
        "-t",
        "--theme",
        action="append",
        default=[],
        help="Only process the named cursor theme (repeatable).",
    )
    parser.add_argument(
        "--size-strategy",
        default="largest",
        help="Which Xcursor size to extract: 'largest' (default), 'smallest', or 'closest:<px>'.",
    )
    parser.add_argument(
        "--add-inherits",
        default="Adwaita",
        help="Fallback theme to add to index.theme if Inherits= is missing (default: Adwaita).",
    )
    parser.add_argument(
        "--no-inherits",
        action="store_true",
        help="Do not modify index.theme files.",
    )
    parser.add_argument(
        "--no-symlink-icons",
        action="store_true",
        help="Do not create ~/.icons -> ~/.local/share/icons symlink when ~/.icons is missing.",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite existing cursors_scalable/ entries.",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing any files.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print per-cursor details.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = parse_args(argv)
    print(ASCII_LOGO)
    print()

    if args.icons_dir is None:
        icons_dirs = [
            Path.home() / ".local" / "share" / "icons",
            Path.home() / ".icons",
        ]
        if not args.no_symlink_icons:
            ensure_icons_symlink(args.dry_run, args.verbose)
    else:
        icons_dirs = [p.expanduser() for p in args.icons_dir]

    if args.system:
        icons_dirs.append(Path("/usr/share/icons"))

    themes = collect_themes(icons_dirs, set(args.theme))
    if not themes:
        print("No cursor themes with a cursors/ directory found.", file=sys.stderr)
        return 1

    inherits = None if args.no_inherits else args.add_inherits
    for name, real_dir in themes:
        print(f"Processing {name} ({real_dir})...")
        files_done, links_done = process_theme(
            real_dir,
            size_strategy=args.size_strategy,
            inherits=inherits,
            force=args.force,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        print(f"  -> {files_done} cursor(s) generated, {links_done} symlink(s) created")

    if args.dry_run:
        print("Dry run complete; no files were modified.")
    else:
        print("Done. Log out and back in (or toggle your cursor theme) to reload GNOME Shell.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
