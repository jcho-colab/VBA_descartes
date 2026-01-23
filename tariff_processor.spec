# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for FTA Tariff Processor
Usage: pyinstaller tariff_processor.spec
"""

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src', 'src'),
        ('HS_IMP_v6.3.xlsm', '.'),
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        'streamlit',
        'streamlit.runtime.scriptrunner.magic_funcs',
        'pandas',
        'lxml',
        'lxml.etree',
        'lxml._elementpath',
        'openpyxl',
        'openpyxl.cell',
        'openpyxl.cell._writer',
        'PIL',
        'PIL.Image',
        'tornado',
        'tornado.web',
        'validators',
        'validators.url',
        'watchdog',
        'watchdog.observers',
        'click',
        'toml',
        'pytz',
        'dateutil',
        'altair',
        'plotly',
        'packaging',
        'packaging.version',
        'packaging.specifiers',
        'packaging.requirements',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'numpy.f2py',
        'IPython',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FTA_Tariff_Processor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False to hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)
