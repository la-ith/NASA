"""Run with python tools/run_pilot_validation.py from backend/. Reuses hash-verified raw downloads."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.validation.pilot import run
if __name__=='__main__':asyncio.run(run())
