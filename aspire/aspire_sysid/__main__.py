"""Allow ``python -m aspire_sysid`` as an equivalent of the console script ``aspire``."""

import sys

from .cli import main

sys.exit(main())
