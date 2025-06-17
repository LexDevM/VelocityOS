# -*- mode: python ; coding: utf-8 -*-

# Definición de la variable que faltaba
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('config', 'config'),
        ('bin', 'bin'),
        ('.venv/Lib/site-packages/PyQt6/Qt6/plugins/imageformats', 'PyQt6/Qt6/plugins/imageformats')
    ],
    hiddenimports=['pyqtgraph.graphicsItems', 'pynvml'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VelocityOS',
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
    version='version.txt',
    icon='assets\\icons\\velocityos.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    a.zipfiles,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VelocityOS'
)