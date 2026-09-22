#!/usr/bin/env python3
"""
Generate conda environment.yml or a shell script of source-build install steps
by scanning tool definitions in tools/.

Usage:
  python make_env.py                  # emit environment.yml to stdout
  python make_env.py --install-steps  # emit install_steps.sh to stdout
"""
from __future__ import annotations

import argparse
import importlib
import inspect
import pkgutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _get_compressor_classes():
    import tools
    from tools.base import BaseCompressor

    classes = []
    for _importer, module_name, _ispkg in pkgutil.iter_modules(tools.__path__):
        if module_name == "base":
            continue
        mod = importlib.import_module(f"tools.{module_name}")
        for _name, cls in inspect.getmembers(mod, inspect.isclass):
            if (
                issubclass(cls, BaseCompressor)
                and cls is not BaseCompressor
                and cls.__module__ == mod.__name__
            ):
                classes.append(cls)
    return classes


def _make_environment_yml(classes) -> str:
    base_deps = ["python>=3.9"]
    deps: list[str] = list(base_deps)
    seen_deps: set[str] = set(base_deps)
    channels: list[str] = []
    seen_channels: set[str] = set()

    for cls in classes:
        for dep in cls.conda_deps:
            if dep not in seen_deps:
                deps.append(dep)
                seen_deps.add(dep)
        for ch in cls.conda_channels:
            if ch not in seen_channels:
                channels.append(ch)
                seen_channels.add(ch)

    lines = ["name: base", "channels:"]
    for ch in channels:
        lines.append(f"  - {ch}")
    lines.append("dependencies:")
    for dep in deps:
        lines.append(f"  - {dep}")
    return "\n".join(lines) + "\n"


def _make_install_steps_sh(classes) -> str:
    lines = ["#!/bin/bash", "set -euo pipefail", ""]
    for cls in classes:
        if cls.install_steps:
            lines.append(f"# {cls.name}")
            lines.extend(cls.install_steps)
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-steps", action="store_true",
                        help="Output shell install steps instead of environment.yml")
    args = parser.parse_args()

    classes = _get_compressor_classes()
    if args.install_steps:
        print(_make_install_steps_sh(classes))
    else:
        print(_make_environment_yml(classes))


if __name__ == "__main__":
    main()
