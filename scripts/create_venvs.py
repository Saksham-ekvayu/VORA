from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REQUIREMENTS_TXT = "requirements.txt"
OK = "  ok"


def get_service_dirs(root: Path) -> list[Path]:
    services_dir = root / "services"
    if not services_dir.is_dir():
        raise FileNotFoundError(f"Missing services directory: {services_dir}")

    service_dirs = [p for p in services_dir.iterdir() if p.is_dir() and (p / REQUIREMENTS_TXT).is_file()]

    gateway_dir = root / "gateway"
    if gateway_dir.is_dir() and (gateway_dir / REQUIREMENTS_TXT).is_file():
        service_dirs.append(gateway_dir)

    return sorted(service_dirs)


def create_venv(service_dir: Path, python_executable: str) -> Path:
    venv_dir = service_dir / ".venv"
    if venv_dir.exists():
        print(f"  Skipping existing venv: {venv_dir}")
        return venv_dir

    print("  Creating venv...")
    try:
        subprocess.run([python_executable, "-m", "venv", str(venv_dir)], check=True)
        print(OK)
        return venv_dir
    except subprocess.CalledProcessError as e:
        print(f"  ERROR: Failed to create venv. {e}")
        raise


def install_requirements(venv_dir: Path, service_dir: Path) -> None:
    if sys.platform == "win32":
        python_path = venv_dir / "Scripts" / "python.exe"
    else:
        python_path = venv_dir / "bin" / "python"

    if not python_path.exists():
        raise FileNotFoundError(f"Python executable not found in venv: {python_path}")

    requirements_file = service_dir / REQUIREMENTS_TXT
    if not requirements_file.exists():
        raise FileNotFoundError(f"requirements.txt not found in {service_dir}")

    print("  Installing dependencies...")
    try:
        subprocess.run(
            [str(python_path), "-m", "pip", "install", "-r", str(requirements_file)],
            check=True,
            cwd=service_dir,
        )
        print(OK)
    except subprocess.CalledProcessError as e:
        print(f"  ERROR: Failed to install dependencies. {e}")
        raise


def install_shared_package(venv_dir: Path, shared_dir: Path) -> None:
    if sys.platform == "win32":
        python_path = venv_dir / "Scripts" / "python.exe"
    else:
        python_path = venv_dir / "bin" / "python"

    if not python_path.exists():
        raise FileNotFoundError(f"Python executable not found in venv: {python_path}")

    if not shared_dir.is_dir():
        print(f"  WARNING: Shared directory not found: {shared_dir}")
        return

    print("  Installing shared package in editable mode...")
    try:
        subprocess.run(
            [str(python_path), "-m", "pip", "install", "-e", str(shared_dir)],
            check=True,
            cwd=shared_dir,
        )
        print(OK)
    except subprocess.CalledProcessError as e:
        print(f"  ERROR: Failed to install shared package. {e}")
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create virtual environments in every service folder.")
    parser.add_argument(
        "--install",
        action="store_true",
        help="Also install each service requirements.txt into the created venv.",
    )
    parser.add_argument(
        "--install-shared",
        action="store_true",
        help="Install the shared package in editable mode.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python interpreter to use for venv creation.",
    )
    parser.add_argument(
        "--root",
        default="backend",
        help="Path to the vora_fastapi repository root from this script location.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    # If --root is relative, resolve it from the parent directory of scripts
    if not Path(args.root).is_absolute():
        root = (script_dir.parent / args.root).resolve()
    else:
        root = Path(args.root).resolve()

    print()
    print("=" * 60)
    print("Creating Virtual Environments")
    print("=" * 60)
    print()

    try:
        service_dirs = get_service_dirs(root)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1

    if not service_dirs:
        print("No service directories with requirements.txt found.")
        return 1

    print(f"Found {len(service_dirs)} service(s):")
    for service_dir in service_dirs:
        print(f"  - {service_dir.relative_to(root)}")
    print()

    # Install shared package first if requested
    if args.install_shared:
        shared_dir = root / "shared"
        if service_dirs:
            venv_dir = service_dirs[0] / ".venv"
            print("Installing shared package...")
            try:
                install_shared_package(venv_dir, shared_dir)
            except FileNotFoundError as e:
                print(f"ERROR: {e}")
                return 1
            print()

    for service_dir in service_dirs:
        print(f"Processing {service_dir.name}...")
        try:
            venv_dir = create_venv(service_dir, args.python)
            if args.install:
                install_requirements(venv_dir, service_dir)
        except Exception as e:
            print(f"ERROR: {e}")
            return 1
        print()

    print("=" * 60)
    print("Done! Virtual environments created successfully.")
    print("=" * 60)
    print()

    if not args.install:
        print("To install dependencies, run: install_venvs.bat")

    print()
    print("To activate a service venv:")
    print("  Windows PowerShell: .\\services\\<service-name>\\.venv\\Scripts\\Activate.ps1")
    print("  Windows CMD: .\\services\\<service-name>\\.venv\\Scripts\\activate.bat")
    print("  macOS/Linux: source ./services/<service-name>/.venv/bin/activate")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
