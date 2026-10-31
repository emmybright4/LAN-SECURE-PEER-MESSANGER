# -*- mode: python ; coding: utf-8 -*-

"""
SecureLocal Chat - PyInstaller Spec File
Compatible with Python 3.14
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Collect template files
templates = []
if os.path.exists('templates'):
    for root, dirs, files in os.walk('templates'):
        for file in files:
            templates.append((os.path.join(root, file), root))

# Collect static files
static = []
if os.path.exists('static'):
    for root, dirs, files in os.walk('static'):
        for file in files:
            static.append((os.path.join(root, file), root))

datas = templates + static

# Add Python files
datas += [
    ('security.py', '.'),
    ('database.py', '.'),
    ('network.py', '.'),
]

# Add launcher files to distribution (they won't be in the exe but in dist folder)
# These will be copied separately by the build script

hiddenimports = [
    'flask',
    'flask.json',
    'flask.templating',
    'cryptography',
    'cryptography.fernet',
    'cryptography.hazmat.backends',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.primitives.kdf.pbkdf2',
    'cryptography.hazmat.primitives.ciphers',
    'werkzeug',
    'werkzeug.utils',
    'sqlite3',
    'threading',
    'socket',
    'json',
    'datetime',
    'time',
    'hashlib',
    'base64',
    'secrets',
    'uuid',
    'webbrowser',  # Added for auto-browser opening
]

# Additional hidden imports for Flask
datas += collect_data_files('flask')

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SecureLocalChat',
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
    entitlements_file=None
)
