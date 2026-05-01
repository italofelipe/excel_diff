# -*- mode: python ; coding: utf-8 -*-
import site

a = Analysis(
    ['src\\excel_diff\\main.py'],
    pathex=site.getsitepackages() + [site.getusersitepackages()],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=[
        'openpyxl.cell._writer',
        'rapidfuzz.fuzz',
        'rapidfuzz.process',
        'rapidfuzz.utils',
        'rapidfuzz.distance',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ExcelDiff',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\icon.ico'],
    version='version_file.txt',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ExcelDiff',
)
