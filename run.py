"""
I keep this entrypoint minimal on purpose. I import create_app(), build the app,
and run the dev server when invoked directly. I prefer `python run.py` for
clarity in Windows + PowerShell environments.
"""

import os
from app import create_app


app = create_app()


if __name__ == "__main__":
    # Allow host/port override via environment for Docker/use in CI.
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    app.run(host=host, port=port, debug=True)
