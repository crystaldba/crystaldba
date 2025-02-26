"""Scripts for the Crystal DBA Agent."""

import logging
import os
import subprocess
import sys
import tempfile

logger = logging.getLogger(__name__)


def lint():
    """Run linting."""
    print("Running Ruff lint...")
    try:
        subprocess.run(["ruff", "check", "."], check=True)
        subprocess.run(["ruff", "format", "--check", "."], check=True)
    except subprocess.CalledProcessError:
        sys.exit("Ruff lint failed!")


def check():
    """Run type checking."""
    print("Running Pyright type checking...")
    try:
        subprocess.run(["pyright"], check=True)
    except subprocess.CalledProcessError:
        sys.exit("Pyright check failed!")


def test():
    """Run tests."""
    print("Running pytest...")
    try:
        subprocess.run(["pytest", "-v"], check=True)
    except subprocess.CalledProcessError:
        sys.exit("Tests failed!")


def list_commands():
    """List available commands."""
    print("Available commands:")
    print("  lint         - Run Ruff linter")
    print("  check        - Run Pyright type checker")
    print("  build        - Install dependencies and run checks")
    print("  test         - Run pytest tests")
    print("  list         - Show this help message")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        list_commands()
        sys.exit(1)

    commands = {
        "lint": lint,
        "check": check,
        "test": test,
        "list": list_commands,
    }

    command = sys.argv[1]
    if command not in commands:
        print(f"Unknown command: {command}")
        list_commands()
        sys.exit(1)

    commands[command]()


def build_linux_arm64():
    """Build for Linux ARM64 using Nuitka."""
    print("\n🚀 Building for Linux ARM64...")
    command = [
        "python",
        "-m",
        "nuitka",
        "--standalone",
        "--follow-imports",
        "--assume-yes-for-downloads",
        "--include-package=crystaldba",
        "--include-package=prompt_toolkit",
        "--include-package=sqlalchemy",
        "--include-package=cryptography",
        "--output-dir=build/linux_arm64",
        "--output-filename=crystaldba",
        "crystaldba/cli/main.py",
    ]
    subprocess.run(command, check=True)
    print("✅ Linux ARM64 build complete: build/linux_arm64/main.dist/crystal-client-linux-arm64")


def build_macos_arm64():
    """Build for macOS ARM64 using Nuitka."""
    print("\n🚀 Building for macOS ARM64...")
    command = [
        "python",
        "-m",
        "nuitka",
        "--standalone",
        "--follow-imports",
        "--assume-yes-for-downloads",
        "--include-package=crystaldba",
        "--include-package=tui",
        "--include-package=prompt_toolkit",
        "--include-package=sqlalchemy",
        "--include-package=cryptography",
        "--include-package=pygments",
        "--macos-create-app-bundle",
        "--macos-app-icon=resources/macos/crystal-dba.icns",
        "--output-dir=build/macos_arm64",
        "--output-filename=crystaldba",
        "--include-data-files=tui/tui.scss=tui/tui.scss",
        "--include-data-files=resources/macos/launch.sh=launch.sh",
        "tui/__main__.py",
    ]
    subprocess.run(command, check=True)
    # Rename the app bundle
    os.rename("build/macos_arm64/__main__.app", "build/macos_arm64/Crystal DBA.app")

    # Update Info.plist to use launch.sh as executable
    info_plist_path = "build/macos_arm64/Crystal DBA.app/Contents/Info.plist"
    with open(info_plist_path) as f:
        info_plist = f.read()
    import re
    pattern = re.compile(r'(<key>CFBundleExecutable</key>\s*<string>)crystaldba(</string>)')
    if not pattern.search(info_plist):
        raise ValueError("Could not find CFBundleExecutable pattern in Info.plist")
    info_plist = pattern.sub(r'\1launch.sh\2', info_plist)
    with open(info_plist_path, "w") as f:
        f.write(info_plist)


    # Create a DMG file using dmgbuild
    print("📦 Creating DMG file using dmgbuild...")
    dmg_path = "build/macos_arm64/crystaldba.dmg"
    app_path = "build/macos_arm64/Crystal DBA.app"

    # Run dmgbuild command
    try:
        import dmgbuild

        dmgbuild.build_dmg(
            filename=dmg_path,
            volume_name="CrystalDBA",
            settings={
                "symlinks": {"Applications": "/Applications"},
                "icon_locations": {
                    "Crystal DBA.app": (200, 190),
                    "Applications": (600, 185)
                },
                "window_rect": ((200, 120), (800, 400)),
                "files": [(app_path, "Crystal DBA.app")],
            }
        )
        print(f"✅ DMG file created: {dmg_path}")
    except Exception as e:
        print("❌ Failed to create DMG file.")
        print("Error output:")
        print(e)
        sys.exit(1)


def build_linux_amd64():
    """Build for Linux AMD64 (x86_64) from ARM64 using Nuitka with cross-compilation."""
    print("\n🚀 Building for Linux AMD64 (cross-compiling from ARM64)...")
    # You might need to install cross-compilation tools for this step.
    # Ensure `gcc`, `g++`, `multilib` support for cross-compiling is available.

    # Set the environment for cross-compilation
    cross_compile_env = {
        "CROSS_COMPILE": "x86_64-linux-gnu-",  # Set cross-compiler prefix
        "CC": "x86_64-linux-gnu-gcc",  # Set the cross-compiler C compiler
        "CXX": "x86_64-linux-gnu-g++",  # Set the cross-compiler C++ compiler
    }

    # Command to cross-compile for x86_64
    command = [
        "python",
        "-m",
        "nuitka",
        "--standalone",
        "--follow-imports",
        "--assume-yes-for-downloads",
        "--include-package=crystaldba",
        "--include-package=prompt_toolkit",
        "--include-package=sqlalchemy",
        "--include-package=cryptography",
        "--output-dir=build/linux_amd64",
        "--output-filename=crystaldba",
        "crystaldba/cli/main.py",
    ]
    subprocess.run(command, check=True, env={**cross_compile_env, **dict(os.environ)})
    print("✅ Linux AMD64 build complete: build/linux_amd64/main.dist/crystal-client-linux-amd64")


def build_windows_arm64():
    """Build for Windows ARM64 using Nuitka."""
    print("\n🚀 Building for Windows ARM64...")
    command = [
        "python",
        "-m",
        "nuitka",
        "--standalone",
        "--follow-imports",
        "--assume-yes-for-downloads",
        "--include-package=crystaldba",
        "--include-package=tui",
        "--include-package=prompt_toolkit",
        "--include-package=sqlalchemy",
        "--include-package=cryptography",
        "--include-package=pygments",
        "--windows-icon-from-ico=resources/windows/crystal-dba.ico",
        "--windows-company-name=Crystal DBA",
        "--windows-product-name=Crystal DBA",
        "--windows-file-version=1.0.0.0",
        "--windows-product-version=1.0.0.0",
        "--output-dir=build/windows_arm64",
        "--output-filename=crystaldba",
        "--include-data-files=tui/tui.scss=tui/tui.scss",
        "tui/__main__.py",
    ]
    subprocess.run(command, check=True)
    print("✅ Windows ARM64 build complete: build/windows_arm64/__main__.dist/crystaldba.exe")
