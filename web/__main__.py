"""python -m web [--host 127.0.0.1] [--port 8000] [--data-dir var/memledger]

Without $MEMLEDGER_USERS the console runs in open mode (pick any demo user), which is only allowed on localhost.
"""

from __future__ import annotations

import argparse
import os
import sys


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m web", description=__doc__.splitlines()[0])
    ap.add_argument("--host", default=os.environ.get("MEMLEDGER_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("MEMLEDGER_PORT", "8000")))
    ap.add_argument("--data-dir", default=os.environ.get("MEMLEDGER_DATA_DIR", "var/memledger"))
    ap.add_argument("--allow-open", action="store_true", help="open mode on a non-local host (demos only)")
    a = ap.parse_args(argv)
    if not os.environ.get("MEMLEDGER_USERS") and a.host not in ("127.0.0.1", "localhost", "::1") \
            and not a.allow_open:
        print("refusing open mode on a public address: set MEMLEDGER_USERS (see web/auth.py) or pass --allow-open",
              file=sys.stderr)
        return 2
    import uvicorn

    from web.api import create_app

    uvicorn.run(create_app(a.data_dir), host=a.host, port=a.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
