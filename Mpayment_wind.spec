# -*- mode: python ; coding: utf-8 -*-
"""
Build Windows (onedir) : pyinstaller --noconfirm Mpayment_wind.spec
Prérequis : dépôt `qt_common` au même niveau que `MPayments` (dossier parent).
Sortie : dist/Business/Business.exe — base SQLite et LICENCE à côté du .exe.

Parallels / chemin ``\\\\Mac\\Home\\...`` : ne pas mélanger un ancien build macOS
(dossier _internal avec Python.framework) — PermissionError/WinError 5 ou 145.
Nettoyez d’abord (voir clean_build_win.ps1 ou build_windows.bat) ou buildez depuis C:\\.
"""
import os

from PyInstaller.utils.hooks import collect_submodules

try:
    SPEC_ROOT = os.path.dirname(os.path.abspath(SPEC))
except NameError:
    SPEC_ROOT = os.getcwd()

static_dir = os.path.join(SPEC_ROOT, "static")
images_dir = os.path.join(static_dir, "images")
icon_path = os.path.join(images_dir, "logo.ico")
main_script = os.path.join(SPEC_ROOT, "main.py")

# Même arbre que main.py dev : ../qt_common/src sur le PATH d’import
qt_common_src = os.path.normpath(os.path.join(SPEC_ROOT, "..", "qt_common", "src"))
common_pkg = os.path.join(qt_common_src, "Common")

# xlsxwriter : sous Windows, l’analyse statique peut omettre des sous-modules ;
# Common.exports_xlsx est importé tardivement depuis l’UI.
_xlsx_hidden = collect_submodules("xlsxwriter")

a = Analysis(
    [main_script],
    pathex=[SPEC_ROOT, qt_common_src],
    binaries=[],
    datas=[
        (images_dir, os.path.join("static", "images")),
        (os.path.join(common_pkg, "cimages"), os.path.join("Common", "cimages")),
    ],
    hiddenimports=[
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.QtPrintSupport",
        "PyQt6.QtPdf",
        "PyQt6.QtPdfWidgets",
        "peewee",
        "peewee_migrate",
        "playhouse.migrate",
        "bcrypt",
        "requests",
        "psutil",
        "PIL",
        "PIL.Image",
        "xlsxwriter",
        "Common.exports_xlsx",
        "reportlab",
        "gettext_windows",
        "models",
        "database",
        "configuration",
        "ui.debt_manager",
        "ui.menubar",
        "ui.menutoolbar",
        "ui.mainwindow",
        "Common.migrations",
        "Common.migrations.run_migrations",
        "Common.migrations.migration_tracker",
    ]
    + _xlsx_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Business",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if os.path.isfile(icon_path) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Business",
)
