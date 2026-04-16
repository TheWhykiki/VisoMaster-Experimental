from pathlib import Path


def project_root_path() -> Path:
    return Path(__file__).resolve().parents[2]


def project_path(*parts: str) -> Path:
    return project_root_path().joinpath(*parts)


def ensure_project_dir(*parts: str) -> Path:
    path = project_path(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_project_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return project_root_path() / candidate
