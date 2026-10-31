#!/usr/bin/env python3
"""
SecureLocal Chat Builder - Complete Working Version for Python 3.14
FIXED: Removed emojis from batch files to prevent encoding errors
"""

import os
import shutil
import sys
import subprocess
import site

def check_python_version():
    """Check Python version and warn if not 3.14"""
    version = sys.version_info
    print(f"🐍 Python version: {version.major}.{version.minor}.{version.micro}")
    if version.major == 3 and version.minor >= 14:
        print("✅ Python 3.14+ detected - good!")
        return True
    else:
        print(f"⚠️  Warning: You're using Python {version.major}.{version.minor}")
        print("   Recommended: Python 3.14")
        return False

def install_dependencies():
    """Install required packages"""
    print("\n📦 Checking dependencies...")
    
    packages = [
        'flask',
        'cryptography',
        'pyinstaller',
        'werkzeug'
    ]
    
    for package in packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"   ✅ {package} already installed")
        except ImportError:
            print(f"   📥 Installing {package}...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', package], 
                         capture_output=True)

def create_icon():
    """Create a simple icon file if it doesn't exist"""
    if os.path.exists('app.ico'):
        return True
    
    print("\n🖼️  Creating default icon...")
    try:
        # Try to create a simple icon using built-in modules
        icon_data = bytearray([
            0,0,1,0,1,0,16,16,0,0,1,0,32,0,52,4,
            0,0,22,0,0,0,40,0,0,0,16,0,0,0,32,0,
            0,0,1,0,32,0,0,0,0,0,0,4,0,0,0,0,
            0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
        ]) + bytes([0]*1088)  # Padding to make valid ICO
        
        with open('app.ico', 'wb') as f:
            f.write(icon_data)
        print("   ✅ Default icon created")
        return True
    except:
        print("   ⚠️  Could not create icon - will build without one")
        return False

def create_launcher_files():
    """Create launcher batch and VBS files - FIXED: No emojis"""
    print("\n🚀 Creating launcher files...")
    
    # Create batch launcher - NO EMOJIS
    batch_content = """@echo off
title SecureLocal Chat Launcher
echo ========================================
echo    SECURELOCAL CHAT LAUNCHER
echo ========================================
echo.

echo [1/3] Starting SecureLocal Chat...
start "" "%~dp0SecureLocalChat.exe"

echo [2/3] Waiting for app to initialize...
timeout /t 3 >nul

echo [3/3] Opening browser...
start http://localhost:5000

echo.
echo App started successfully!
echo The app is running in the background
echo Browser should open automatically
echo.
echo Press any key to close this window...
pause >nul
exit"""
    
    # FIXED: Use utf-8 encoding for batch file
    with open('Start_Chat.bat', 'w', encoding='utf-8') as f:
        f.write(batch_content)
    print("   ✅ Created Start_Chat.bat")
    
    # Create VBS silent launcher - NO EMOJIS
    vbs_content = """' SecureLocal Chat Silent Launcher
Set WshShell = CreateObject("WScript.Shell")

' Get the directory where this script is located
strPath = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))

' Launch the executable silently
WshShell.Run Chr(34) & strPath & "SecureLocalChat.exe" & Chr(34), 0, False

' Wait for app to start
WScript.Sleep 3000

' Open browser
WshShell.Run "http://localhost:5000"
"""
    
    # FIXED: Use utf-8 encoding for VBS file
    with open('Launch_Chat.vbs', 'w', encoding='utf-8') as f:
        f.write(vbs_content)
    print("   ✅ Created Launch_Chat.vbs")

def create_simple_spec():
    """Create a minimal spec file that works with Python 3.14"""
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

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
'''
    
    with open('SecureLocalChat.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    print("✅ Spec file created")

def build_with_pyinstaller():
    """Run PyInstaller with verbose output"""
    print("\n🔨 Building executable with PyInstaller...")
    print("   This may take 3-5 minutes...\n")
    
    # Run PyInstaller with full output
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--log-level', 'INFO',
        'SecureLocalChat.spec'
    ]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Print output in real-time
    for line in process.stdout:
        print(f"   {line.strip()}")
    
    process.wait()
    return process.returncode

def create_readme():
    """Create a simple README file - NO EMOJIS"""
    readme_content = """SECURELOCAL CHAT - USER GUIDE
================================

INSTALLATION:
-----------
1. Run Launch_Chat.vbs (double-click it)
2. If Windows Firewall asks, click "ALLOW ACCESS"
3. Browser will open automatically
4. Create account or login
5. Click "Auto-Exchange Keys"
6. Select user and start chatting!

FILES INCLUDED:
------------
* SecureLocalChat.exe - Main program
* Launch_Chat.vbs - SILENT LAUNCHER (recommended)
* Start_Chat.bat - LAUNCHER WITH WINDOW (for debugging)

TROUBLESHOOTING:
-------------
* Can't see other users? Check Windows Firewall
* Can't send messages? Verify other user is online
* Keys not working? Click "Auto-Exchange Keys" again
* App not opening? Run Start_Chat.bat to see errors

PORTS USED:
---------
* UDP 6666 - Discovery
* TCP 6667 - Messaging

IMPORTANT:
--------
Always use Launch_Chat.vbs to start the app!
It runs silently and opens your browser automatically.

Email: support@example.com
"""
    
    with open('README.txt', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print("✅ README created")

def create_batch_file():
    """Create a batch file for easy launching - NO EMOJIS"""
    batch_content = """@echo off
echo Starting SecureLocal Chat...
start "" "%~dp0SecureLocalChat.exe"
echo Chat app launched! Check system tray.
echo Opening browser...
timeout /t 3 >nul
start http://localhost:5000
echo Done!
"""
    
    with open('Start_Chat.bat', 'w', encoding='utf-8') as f:
        f.write(batch_content)
    print("✅ Start script created")

def main():
    print("="*70)
    print("SECURELOCAL CHAT - BUILD SYSTEM")
    print("="*70)
    
    # Check Python version
    check_python_version()
    
    # Install dependencies
    install_dependencies()
    
    # Check required files
    required_files = [
        'app.py', 'security.py', 'database.py', 'network.py',
        'templates/chat.html', 'templates/login.html', 'templates/register.html'
    ]
    
    print("\n📋 Checking required files...")
    missing = []
    for file in required_files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file}")
            missing.append(file)
    
    if missing:
        print("\n❌ ERROR: Missing required files!")
        sys.exit(1)
    
    # Create icon if needed
    create_icon()
    
    # Create launcher files
    create_launcher_files()
    
    # Create README
    create_readme()
    
    # Create spec file
    create_simple_spec()
    
    # Ask to continue
    print("\n" + "="*70)
    response = input("Proceed with build? (y/n): ").strip().lower()
    
    if response != 'y':
        print("Build cancelled.")
        return
    
    # Build with PyInstaller
    result = build_with_pyinstaller()
    
    if result == 0:
        print("\n" + "="*70)
        print("✅ BUILD COMPLETED SUCCESSFULLY!")
        print("="*70)
        print("\n📁 Your executable is ready:")
        print(f"   📂 Location: {os.path.abspath('dist/SecureLocalChat.exe')}")
        
        # Copy launcher files to dist folder
        print("\n📋 Copying launcher files to dist folder...")
        shutil.copy("Start_Chat.bat", "dist/")
        shutil.copy("Launch_Chat.vbs", "dist/")
        shutil.copy("README.txt", "dist/")
        print("   ✅ Launcher files copied")
        
        # Create distribution folder
        print("\n📦 Creating distribution package...")
        dist_folder = "SecureLocalChat_Distribution"
        if os.path.exists(dist_folder):
            shutil.rmtree(dist_folder)
        
        os.makedirs(dist_folder)
        
        # Copy all files
        if os.path.exists("dist/SecureLocalChat.exe"):
            shutil.copy("dist/SecureLocalChat.exe", dist_folder)
        shutil.copy("dist/Start_Chat.bat", dist_folder)
        shutil.copy("dist/Launch_Chat.vbs", dist_folder)
        shutil.copy("dist/README.txt", dist_folder)
        
        # Create ZIP
        shutil.make_archive("SecureLocalChat_v1.0", 'zip', dist_folder)
        print(f"   ✅ Created SecureLocalChat_v1.0.zip")
        
        print("\n" + "="*70)
        print("🎉 All done! Share these files:")
        print(f"   • SecureLocalChat_v1.0.zip")
        print("\n📝 Instructions for users:")
        print("   1. Extract the ZIP file")
        print("   2. Double-click Launch_Chat.vbs")
        print("   3. Browser opens automatically")
        print("   4. Login and start chatting!")
        print("="*70)
        
    else:
        print("\n❌ BUILD FAILED!")
        print("\n💡 Alternative method:")
        print("   1. Create a virtual environment with Python 3.11:")
        print("      python3.11 -m venv venv")
        print("      venv\\Scripts\\activate")
        print("      pip install -r requirements.txt")
        print("      pyinstaller --onefile --windowed app.py")
        print("\n   2. Or use auto-py-to-exe:")
        print("      pip install auto-py-to-exe")
        print("      auto-py-to-exe")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nBuild cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nPress Enter to exit...")