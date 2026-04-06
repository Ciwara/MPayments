import sys
from pathlib import Path

"""
MPayments dépend de `qt_common` (package `Common`).
En dev, on privilégie la version locale `../qt_common/src` pour éviter
les divergences avec une version installée dans site-packages.
"""
_qt_common_src = (Path(__file__).resolve().parent.parent / "qt_common" / "src").resolve()
if _qt_common_src.exists():
    sys.path.insert(0, str(_qt_common_src))

from Common.cmain import cmain  # noqa: E402

if __name__ == "__main__":
    if cmain():
        sys.exit(0)
