from __future__ import annotations

import re

REMOTE_URL_RE = re.compile(r"https?://|//[A-Za-z0-9.-]+(?:/|$)")
NON_PATH_TOKEN_RE = re.compile(r"^(?:-?(?:\d+(?:\.\d+)?|\.\d+)(?:\^2|%|x)?|e\.g\.?|i\.e\.?)$", re.I)
