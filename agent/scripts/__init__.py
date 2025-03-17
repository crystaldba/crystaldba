"""Scripts for the Crystal DBA Agent."""

import logging
import os
import subprocess
import sys

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
        "--assume-yes-for-downloads",
        "--include-package=crystaldba.cli",
        "--include-package=crystaldba.shared",
        "--include-package=prompt_toolkit",
        "--include-package=sqlalchemy",
        "--include-package=cryptography",
        "--output-dir=build/linux_arm64",
        "--output-filename=crystaldba",
        # "--report=compilation-report.xml",
        "tui/__main__.py",
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
        "--macos-create-app-bundle",
        "--standalone",
        "--assume-yes-for-downloads",
        "--include-package=crystaldba.cli",
        "--include-package=crystaldba.shared",
        "--include-package=prompt_toolkit",
        "--include-package=sqlalchemy",
        "--include-package=cryptography",
        "--output-dir=build/macos_arm64",
        "--output-filename=crystaldba",
        # "--report=compilation-report.xml",
        "tui/__main__.py",
    ]
    subprocess.run(command, check=True)
    print("✅ macOS ARM64 build complete: build/macos_arm64/main.dist/crystal-client-macos-arm64")


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
        # "LD_LIBRARY_PATH": "/usr/lib/x86_64-linux-gnu/",
    }

    # Command to cross-compile for x86_64
    command = [
        "python",
        "-m",
        "nuitka",
        "--standalone",
        "--noinclude-pytest-mode=nofollow",
        "--noinclude-setuptools-mode=nofollow",
        "--include-package-data=tui",
        "--assume-yes-for-downloads",
        "--include-package=crystaldba.cli",
        "--include-package=crystaldba.shared",
        "--include-package=cryptography",
        "--include-package=litellm",
        "--include-package=prompt_toolkit",
        "--include-package=pydantic",
        # "--include-package=pygments",
        # "--include-package=pyperclip",
        "--include-package=rich",
        "--include-package=sqlalchemy",
        "--include-package=textual",
        "--include-package=tui",
        "--static-libpython=yes",
        "--include-data-files=tui/tui.scss=tui/tui.scss",
        "--output-dir=build/linux_amd64",
        "--output-filename=crystaldba",
        # "--report=private/compilation-report.xml",
        "tui/__main__.py",
    ]
    subprocess.run(command, check=True, env={**cross_compile_env, **dict(os.environ)})
    print("✅ Linux AMD64 build complete: build/linux_amd64/main.dist/crystal-client-linux-amd64")
