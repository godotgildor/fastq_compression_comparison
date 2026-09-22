from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from tools.base import BaseCompressor

_registry: dict[str, Type[BaseCompressor]] = {}


def _load() -> None:
    if _registry:
        return
    import tools
    from tools.base import BaseCompressor

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
                _registry[cls.name] = cls


def get_all_compressor_classes() -> list[Type[BaseCompressor]]:
    _load()
    return list(_registry.values())


def get_compressor_class(name: str) -> Type[BaseCompressor]:
    _load()
    return _registry[name]
