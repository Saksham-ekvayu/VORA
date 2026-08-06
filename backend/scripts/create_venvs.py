from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def get_service_dirs(root: Path) -> list[Path]:
    services_dir = root / "services"
    if not services_dir.is_dir():
        raise FileNotFoundError(f"Missing services directory: {services_dir}")

    service_dirs = [p for p in services_dir.iterdir() if p.is_dir() and (p / "requirements.txt").is_file()]

    gateway_dir = root / "gateway"
    if gateway_dir.is_dir() and (gateway_dir / "requirements.txt").is_file():
        service_dirs.append(gateway_dir)

    return sorted(service_dirs)


def create_venv(service_dir: Path, python_executable: str) -> Path:
    venv_dir = service_dir / ".venv"
    if venv_dir.exists():
        print(f"Skipping existing venv: {venv_dir}")
        return venv_dir

    print(f"Creating venv in {service_dir}")
    subprocess.run([python_executable, "-m", "venv", str(venv_dir)], check=True)
    return venv_dir


def install_requirements(venv_dir: Path, service_dir: Path) -> None:
    if sys.platform == "win32":
        python_path = venv_dir / "Scripts" / "python.exe"
    else:
        python_path = venv_dir / "bin" / "python"

    if not python_path.exists():
        raise FileNotFoundError(f"Python executable not found in venv: {python_path}")

    requirements_file = service_dir / "requirements.txt"
    if not requirements_file.exists():
        raise FileNotFoundError(f"requirements.txt not found in {service_dir}")

    print(f"Installing dependencies for {service_dir.name}")
    subprocess.run(
        [str(python_path), "-m", "pip", "install", "-r", str(requirements_file)],
        check=True,
        cwd=service_dir,
    )


def install_shared_package(venv_dir: Path, shared_dir: Path) -> None:
    if sys.platform == "win32":
        python_path = venv_dir / "Scripts" / "python.exe"
    else:
        python_path = venv_dir / "bin" / "python"

    if not python_path.exists():
        raise FileNotFoundError(f"Python executable not found in venv: {python_path}")

    if not shared_dir.is_dir():
        raise FileNotFoundError(f"Shared directory not found: {shared_dir}")

    print(f"Installing shared package in editable mode")
    subprocess.run(
        [str(python_path), "-m", "pip", "install", "-e", str(shared_dir)],
        check=True,
        cwd=shared_dir,
    )


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
        default="..",
        help="Path to the vora_fastapi repository root from this script location.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = (Path(__file__).resolve().parent / args.root).resolve()
    service_dirs = get_service_dirs(root)

    if not service_dirs:
        print("No service directories with requirements.txt found.")
        return 1

    print(f"Found {len(service_dirs)} service(s) to process.")

    # Install shared package first if requested
    if args.install_shared:
        shared_dir = root / "shared"
        venv_dir = service_dirs[0] / ".venv"
        print(f"\n---\nInstalling shared package")
        try:
            install_shared_package(venv_dir, shared_dir)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return 1

    for service_dir in service_dirs:
        print(f"\n---\nProcessing {service_dir.name}")
        venv_dir = create_venv(service_dir, args.python)
        if args.install:
            install_requirements(venv_dir, service_dir)

    print("\nDone. To activate a service venv:")
    print("Windows PowerShell: .\\.venv\\Scripts\\Activate.ps1")
    print("Windows CMD: .\\.venv\\Scripts\\activate")
    print("macOS/Linux: source .venv/bin/activate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
