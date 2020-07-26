#! /usr/bin/env python3
"""Script to cleanup the fonts in this folder."""

import logging
import os
from pathlib import Path
import re
import sys
import typing


ARCHIVE_DIR = Path("./archive.d")
"""Directory where archives will be kept."""

ELIMINATIONS = (
    "Windows Compatible",
    "Nerd Font Complete Mono",
    "Nerd Font Complete",
    "Nerd Font Mono",
    "Nerd Font",
    "Complete",
)

PathList = typing.List[Path]

LOG = logging.getLogger(__name__)
"""Module's logger instance."""

def archive(asset: Path, *, dry_run: bool = False) -> None:
    """Transfers an asset into the archive folder."""
    if not ARCHIVE_DIR.exists():
        LOG.info("Create archive directory.")
        ARCHIVE_DIR.mkdir()

    # Move the file to a new destination
    archive = Path(ARCHIVE_DIR / asset.name)
    if not dry_run:
        asset.rename(archive)


def eliminate(asset: Path, files: PathList, pattern: str, *, dry_run: bool = False) -> bool:
    """Archive asset if a file exists which has the name minus pattern."""
    reduced_name = asset.name.replace(f" {pattern}.", ".")
    if reduced_name != asset.name:
        if Path(reduced_name) in files:
            LOG.info("Archive %s for %s", asset.name, reduced_name)
            archive(asset, dry_run=dry_run)
            return True
    return False


def font_files(iterable: typing.Iterable[typing.Any]) -> typing.List[Path]:
    """Returns a list of font files from a collection of Paths."""
    return [Path(p) for p in iterable if p.name.lower().endswith((".otf", ".ttf"))]


def scan_fonts(font_path: str = ".", *, dry_run: bool = False) -> int:
    eliminations = 0
    files = font_files(os.scandir(font_path))
    for fontfile in files:
        if any(eliminate(fontfile, files, pattern, dry_run=dry_run) for pattern in ELIMINATIONS):
            eliminations += 1

    return eliminations


def down_names(font_path: str = ".", *, dry_run: bool = False) -> int:
    renames = 0
    for fontfile in font_files(os.scandir(font_path)):
        filename = fontfile.name
        for pattern in ELIMINATIONS:
            filename = filename.replace(f" {pattern}.", ".")
        if filename != fontfile.name:
            new_path = fontfile.parent / filename
            if new_path.exists():
                LOG.warning("Can't down-name %s -> %s: file exists.", fontfile.name, new_path.name)
                archive(fontfile, dry_run=dry_run)
            else:
                LOG.info("Renaming %s -> %s", fontfile.name, new_path.name)
                if not dry_run:
                    fontfile.rename(new_path)
            renames += 1

    return renames


def tag_fonts(font_path: str = ".", dry_run: bool = False) -> None:
    for font in sorted(font_files(os.scandir(font_path))):
        is_mono = "Mono" in font.name
        config = "--mono" if is_mono else ""                    
        if config:
            LOG.info("Configure %s as %s", font, config)
            if not dry_run:
                opt_file = font.with_name(font.name + ".opts")
                with opt_file.open("w") as fh:
                    fh.write(config)


if __name__ == "__main__":
    dry_run = sys.argv[-1] in {"--dry-run", "-n"}
    logging.basicConfig(level=logging.DEBUG)
    scan_fonts(dry_run=dry_run)
    down_names(dry_run=dry_run)
    tag_fonts(dry_run=dry_run)
