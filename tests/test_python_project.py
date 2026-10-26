from pathlib import Path

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]


def requirement_key(requirement: str) -> tuple[str, str]:
    parsed = Requirement(requirement)
    return canonicalize_name(parsed.name), str(parsed.specifier)


def test_uv_project_matches_backend_dependencies():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    requirements = {
        requirement_key(line)
        for line in (ROOT / "app/backend/requirements.in").read_text().splitlines()
        if line and not line.startswith("#")
    }
    assert {requirement_key(line) for line in project["project"]["dependencies"]} == requirements


def test_uv_project_pins_python_and_public_index():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    supported = SpecifierSet(project["project"]["requires-python"])
    assert "3.13.0" in supported
    assert "3.13.17" in supported
    assert "3.12.0" not in supported
    assert "3.14.0" not in supported
    assert "3.15.0" not in supported
    assert (ROOT / ".python-version").read_text().strip() == "3.13"
    assert project["tool"]["uv"]["index"] == [{"name": "pypi", "url": "https://pypi.org/simple", "default": True}]


def test_uv_lock_preserves_backend_pins():
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    versions = {canonicalize_name(package["name"]): package["version"] for package in lock["package"]}
    for line in (ROOT / "app/backend/requirements.txt").read_text().splitlines():
        if not line or line.startswith((" ", "#", "-")):
            continue
        requirement = Requirement(line)
        name = canonicalize_name(requirement.name)
        # The Python 3.10 requirements include backports no longer needed on 3.13.
        if name not in versions and name in {"async-timeout", "exceptiongroup", "taskgroup", "tomli"}:
            continue
        if requirement.marker and not requirement.marker.evaluate():
            continue
        assert versions[name] in requirement.specifier
