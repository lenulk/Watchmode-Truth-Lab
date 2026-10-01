"""Checkout example using the same bounded sample worker as installed starters."""

import runpy
from pathlib import Path

worker = Path(__file__).resolve().parents[1] / "watchmode_truth_lab/assets/file/worker.py"
runpy.run_path(str(worker), run_name="__main__")
