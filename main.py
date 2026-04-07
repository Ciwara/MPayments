import os
import sys
from pathlib import Path

"""
MPayments dépend de `qt_common` (package `Common`).
En dev, on privilégie la version locale `../qt_common/src` pour éviter
les divergences avec une version installée dans site-packages.

Exécutable PyInstaller : CWD = dossier du .exe (chemins relatifs, SQLite, logs).
"""
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

if not getattr(sys, "frozen", False):
    _qt_common_src = (Path(__file__).resolve().parent.parent / "qt_common" / "src").resolve()
    if _qt_common_src.exists():
        sys.path.insert(0, str(_qt_common_src))

from configuration import Config  # noqa: E402

import Common.cstatic as _cstatic  # noqa: E402

_cstatic.LICENSE_REQUIRED = Config.LICENSE_REQUIRED
_cstatic.BACKUP_TO_USB = Config.BACKUP_TO_USB

from Common.cmain import cmain  # noqa: E402

if __name__ == "__main__":
    if cmain():
        sys.exit(0)
