"""
I keep this entrypoint minimal on purpose. I import create_app(), build the app,
and run the dev server when invoked directly. I prefer `python run.py` for
clarity in Windows + PowerShell environments.
"""

from app import create_app


app = create_app()


if __name__ == "__main__":
    # I bind to 127.0.0.1 by default, which matches the acceptance criteria.
    app.run(host="127.0.0.1", port=5000, debug=True)

