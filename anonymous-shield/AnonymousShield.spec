# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('vendor', 'vendor'), ('assets', 'assets'),
           ('../LICENSE', '.'), ('../LICENSE-APACHE', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
# Fora do bundle (ficam no repo): tar-fonte 21 MB (só os extraídos são
# usados) e tor-gencert (só p/ relays).
a.datas = [x for x in a.datas
           if "tor-expert.tar.gz" not in str(x[0]).replace("\\", "/")
           and "tor-gencert" not in str(x[0]).replace("\\", "/")]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AnonymousShield',
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
    icon=['assets/icon.ico'],
)
