"""Locations of the harness's own files.

The configuration folder ``aspire/configs/`` lies next to the package folder
``aspire/aspire_sysid/``. It is found relative to this file, which holds for the source tree
and for an editable installation (``pip install -e aspire``). A non-editable installation does
not carry the configuration folder; every function that reads a configuration file therefore
also accepts an explicit path.
"""

from __future__ import annotations

from pathlib import Path

PACKAGE_DIR: Path = Path(__file__).resolve().parent
"""The folder of the package ``aspire_sysid``."""

HARNESS_DIR: Path = PACKAGE_DIR.parent
"""The folder ``aspire/`` that holds the package and its configuration files."""

CONFIG_DIR: Path = HARNESS_DIR / "configs"
"""The folder ``aspire/configs/`` with ``prices.yaml`` and ``models.yaml``."""


def config_path(name: str) -> Path:
    """Return the path of the configuration file ``name`` in ``aspire/configs/``.

 The file is not required to exist; the caller reports a missing
    file with its path.
    """
    return CONFIG_DIR / name
