"""Allow ``python -m zhaw`` as an alternative to the ``zhaw`` console script."""
from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
