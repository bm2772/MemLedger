import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # eval/ and infra/ are scripts at the repo root, not installed packages
    sys.path.insert(0, str(ROOT))
