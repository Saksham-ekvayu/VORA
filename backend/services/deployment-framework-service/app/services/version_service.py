"""Port of deployment-framework-service-main/src/services/version.service.js."""


def parse_version(version: str) -> dict[str, int]:
    if not version or not isinstance(version, str):
        raise ValueError("Invalid version format")

    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError("Version must be in format X.Y.Z")

    try:
        major, minor, patch = (int(p) for p in parts)
    except ValueError as exc:
        raise ValueError("Version components must be non-negative integers") from exc

    if major < 0 or minor < 0 or patch < 0:
        raise ValueError("Version components must be non-negative integers")

    return {"major": major, "minor": minor, "patch": patch}


def format_version(v: dict[str, int]) -> str:
    return f"{v['major']}.{v['minor']}.{v['patch']}"


def is_valid_version(version: str) -> bool:
    parse_version(version)
    return True


def increment_minor_patch(current_version: str | None) -> str:
    if not current_version:
        return "1.0.0"

    v = parse_version(current_version)
    if v["patch"] >= 9:
        v["minor"] += 1
        v["patch"] = 0
    else:
        v["patch"] += 1
    return format_version(v)


def increment_file_patch(current_version: str | None) -> str:
    return increment_minor_patch(current_version)


def increment_major_patch(current_version: str | None) -> str:
    if not current_version:
        return "1.0.0"
    v = parse_version(current_version)
    v["major"] += 1
    v["minor"] = 0
    v["patch"] = 0
    return format_version(v)


def compare_versions(version1: str, version2: str) -> int:
    v1 = parse_version(version1)
    v2 = parse_version(version2)

    if v1["major"] != v2["major"]:
        return 1 if v1["major"] > v2["major"] else -1
    if v1["minor"] != v2["minor"]:
        return 1 if v1["minor"] > v2["minor"] else -1
    if v1["patch"] != v2["patch"]:
        return 1 if v1["patch"] > v2["patch"] else -1
    return 0


def get_next_version(current_version: str | None, patch_type: str) -> str:
    if not current_version:
        return "1.0.0"
    patch_type = patch_type.lower()
    if patch_type == "minor":
        return increment_minor_patch(current_version)
    if patch_type == "major":
        return increment_major_patch(current_version)
    raise ValueError('Invalid patch type. Must be "minor" or "major"')
