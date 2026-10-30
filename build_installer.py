"""
RuhiPdf Editor - Build & Windows Installer Automation Script
Developer: Md. Abdullah Al Mamun
Email: a.a.mamunbu@gmail.com
GitHub: https://github.com/Mamuntheprogrammer
LinkedIn: https://www.linkedin.com/in/mamuntheprogrammer

Executes:
1. PyInstaller to build a standalone portable executable package.
2. Inno Setup Compiler (ISCC) to package it into a Windows Setup installer.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_iscc() -> str | None:
    """Find Inno Setup Compiler (ISCC.exe) path."""
    candidates = [
        r"C:\Users\Saad\AppData\Local\Programs\Inno Setup 6\ISCC.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    # Check PATH
    iscc_path = shutil.which("iscc")
    if iscc_path:
        return iscc_path
    return None


def main() -> int:
    project_dir = Path(__file__).parent.resolve()
    os.chdir(project_dir)

    print("=" * 60)
    print("RuhiPdf Editor - Windows Build & Installer Generator")
    print("Developer: Md. Abdullah Al Mamun")
    print("=" * 60)

    # 1. Build executable using PyInstaller
    print("\n[Step 1/2] Compiling standalone executable with PyInstaller...")
    pyinstaller_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        str(project_dir / "RuhiPdfEditor.spec"),
    ]
    res = subprocess.run(pyinstaller_cmd)
    if res.returncode != 0:
        print("[ERROR] PyInstaller build failed!")
        return res.returncode

    exe_path = project_dir / "dist" / "RuhiPdfEditor" / "RuhiPdfEditor.exe"
    if not exe_path.exists():
        print(f"[ERROR] Executable not found at {exe_path}")
        return 1

    print(f"[SUCCESS] Executable created: {exe_path}")

    # 2. Package with Inno Setup
    print("\n[Step 2/2] Creating Windows Setup Installer with Inno Setup...")
    iscc_exe = find_iscc()
    if not iscc_exe:
        print("[WARNING] Inno Setup compiler (ISCC.exe) not found.")
        print("You can compile 'installer.iss' manually in Inno Setup Compiler.")
        return 0

    iss_file = project_dir / "installer.iss"
    inno_cmd = [iscc_exe, str(iss_file)]
    res = subprocess.run(inno_cmd)
    if res.returncode != 0:
        print("[ERROR] Inno Setup compilation failed!")
        return res.returncode

    setup_exe = project_dir / "dist" / "installer" / "RuhiPdfEditor_Setup_v1.0.0.exe"
    if setup_exe.exists():
        size_mb = setup_exe.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 60)
        print("[SUCCESS] INSTALLER BUILD COMPLETE!")
        print(f"Installer File: {setup_exe}")
        print(f"File Size:      {size_mb:.2f} MB")
        print("=" * 60)
    else:
        print("[WARNING] Installer was compiled, please check dist/installer/")

    return 0


if __name__ == "__main__":
    sys.exit(main())

