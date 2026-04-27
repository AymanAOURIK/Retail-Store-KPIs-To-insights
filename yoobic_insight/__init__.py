from __future__ import annotations

from pathlib import Path

_SRC_PACKAGE_DIR = Path(__file__).resolve().parent.parent / "src" / "yoobic_insight"
__path__ = [str(_SRC_PACKAGE_DIR)]

exec((_SRC_PACKAGE_DIR / "__init__.py").read_text(encoding="utf-8"))
