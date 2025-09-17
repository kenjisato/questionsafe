from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple

import yaml
from jinja2 import Environment, FileSystemLoader, PackageLoader, ChoiceLoader, select_autoescape
from importlib import resources as _resources
from rich.console import Console

# Shared console for all CLI modules
console = Console()


def load_project_config(cwd: Path) -> dict:
    cfg_path = cwd / "questionsafe.yml"
    if not cfg_path.exists():
        return {}
    try:
        return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def templates_dir_from_config(cwd: Path) -> Path | None:
    cfg = load_project_config(cwd)
    proj = cfg.get("project") if isinstance(cfg, dict) else None
    if isinstance(proj, dict):
        tdir = proj.get("templates")
        if isinstance(tdir, str) and tdir.strip():
            p = Path(tdir)
            if not p.is_absolute():
                p = cwd / p
            return p
    return None


def questions_root_from_config(cwd: Path) -> Path | None:
    cfg = load_project_config(cwd)
    proj = cfg.get("project") if isinstance(cfg, dict) else None
    if isinstance(proj, dict):
        qdir = proj.get("questions")
        if isinstance(qdir, str) and qdir.strip():
            p = Path(qdir)
            if not p.is_absolute():
                p = cwd / p
            return p
    return None


def resolve_out_path(path_str: str, qroot: Path | None) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    base = qroot or Path.cwd()
    return base / p


def package_templates_dir() -> Path:
    try:
        root = _resources.files("questionsafe.cli").joinpath("templates")
        return Path(str(root))
    except Exception:
        return Path(__file__).resolve().parent / "templates"


def list_template_names(templates_dir: Path) -> list[str]:
    names: list[str] = []
    if templates_dir.exists() and templates_dir.is_dir():
        for p in templates_dir.iterdir():
            if p.is_file() and p.name.endswith(".md.j2"):
                names.append(p.name[:-len(".md.j2")])
    names.sort()
    return names


def available_template_names(cwd: Path) -> Tuple[list[str], Path, bool]:
    user_dir = templates_dir_from_config(cwd)
    if user_dir is not None and user_dir.exists():
        return list_template_names(user_dir), user_dir, True
    pkg_dir = package_templates_dir()
    return list_template_names(pkg_dir), pkg_dir, False


def jinja_env(user_dir: Path | None) -> Environment:
    loaders: list = []
    if user_dir is not None and user_dir.exists():
        loaders.append(FileSystemLoader(str(user_dir)))
    loaders.append(PackageLoader("questionsafe.cli", "templates"))
    env = Environment(
        loader=ChoiceLoader(loaders),
        autoescape=select_autoescape(enabled_extensions=(".j2",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


def render_template(name: str, *, context: dict, user_dir: Path | None) -> str:
    env = jinja_env(user_dir)
    tmpl = env.get_template(f"{name}.md.j2")
    # Inject project variables into Jinja context if present
    try:
        cfg = load_project_config(Path.cwd())
        vars_block = cfg.get("variables", {}) if isinstance(cfg, dict) else {}
        if isinstance(vars_block, dict):
            context = dict(context)
            context.setdefault("VARS", vars_block)
    except Exception:
        pass
    return tmpl.render(**context)


def get_current_course(cwd: Path) -> Optional[str]:
    cfg = load_project_config(cwd)
    cur = None
    try:
        cur = cfg.get("course", {}).get("current")
    except Exception:
        cur = None
    return str(cur) if cur else None


def set_current_course(cwd: Path, course_id: str) -> None:
    cfg_path = cwd / "questionsafe.yml"
    cfg = load_project_config(cwd)
    if "course" not in cfg or not isinstance(cfg.get("course"), dict):
        cfg["course"] = {}
    cfg["course"]["current"] = course_id
    if cfg_path.exists():
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            data = {}
        if "course" not in data or not isinstance(data.get("course"), dict):
            data["course"] = {}
        data["course"]["current"] = course_id
        cfg_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    else:
        data = {"course": {"current": course_id}}
        cfg_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")



