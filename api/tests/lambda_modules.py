"""Load the Lambda handlers in infra/lambdas as plain modules, with chosen environment."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

LAMBDAS = Path(__file__).resolve().parents[2] / "infra" / "lambdas"


def load(name: str, monkeypatch: pytest.MonkeyPatch, **env: str) -> ModuleType:
    """A fresh copy of infra/lambdas/<name>/handler.py, read with `env` set."""
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location(f"lambda_{name}", LAMBDAS / name / "handler.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
