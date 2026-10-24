"""MemLedger console: a FastAPI server over MemoryService plus the React UI in web/ui (slides 10, 14, 24).

    pip install -e ".[web]"
    make web            # builds web/ui and serves http://localhost:8000

The server is a thin layer: every read and write goes through LedgerService, and identity (team, role, clearance)
comes from the login token (web/auth.py), never from the browser or the model.
"""
