#!/usr/bin/env python3
"""Superseded by reports/browser_check.py — kept as a thin shim.

The original script only took screenshots and set phone viewports with the
browser window, which cannot go below ~500px on macOS. browser_check.py uses
device-metrics emulation instead and adds real assertions. Run it via:

    PORT=5190 .venv/bin/python reports/browser_check.py
"""
from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("browser_check.py")), run_name="__main__")
