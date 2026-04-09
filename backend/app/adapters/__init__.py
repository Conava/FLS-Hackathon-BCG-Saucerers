"""Adapter registry for pluggable data sources.

Usage
-----
Register a new adapter::

    from app.adapters import register
    from app.adapters.base import DataSource, PatientData

    @register("my_source")
    class MyDataSource:
        name: str = "my_source"

        async def iter_patients(self) -> AsyncIterator[PatientData]:
            ...

Resolve and instantiate an adapter by name::

    from app.adapters import get_source

    source = get_source("csv", data_dir=Path("./data"))
    async for patient_data in source.iter_patients():
        ...

List all registered source names::

    from app.adapters import list_sources

    print(list_sources())  # ['csv', 'fhir', ...]
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.adapters.base import DataSource, PatientData

# ---------------------------------------------------------------------------
# Module-level registry — maps source name → adapter class
# ---------------------------------------------------------------------------

_registry: dict[str, type[DataSource]] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def register(name: str) -> Callable[[type[DataSource]], type[DataSource]]:
    """Class decorator that registers an adapter under ``name``.

    Parameters
    ----------
    name:
        Short identifier (e.g. ``"csv"``, ``"fhir"``). Must be unique.
        Re-registering the same name silently overwrites the previous entry
        (useful during testing).

    Returns
    -------
    Callable
        The original class, unchanged — the decorator only records the
        mapping in ``_registry``.

    Example
    -------
    ::

        @register("csv")
        class CSVDataSource:
            name: str = "csv"
            ...
    """

    def deco(cls: type[DataSource]) -> type[DataSource]:
        _registry[name] = cls
        return cls

    return deco


def get_source(name: str, **kwargs: Any) -> DataSource:
    """Resolve a registered adapter by name and return a new instance.

    Parameters
    ----------
    name:
        The name passed to ``@register``.
    **kwargs:
        Forwarded verbatim to the adapter's ``__init__``.  For example,
        ``get_source("csv", data_dir=Path("./data"))``.

    Returns
    -------
    DataSource
        A freshly constructed adapter instance.

    Raises
    ------
    KeyError
        If ``name`` is not registered. The error message includes the unknown
        name and lists all known sources to help with typo debugging.
    """
    if name not in _registry:
        raise KeyError(
            f"Unknown data source: {name!r}. Known: {sorted(_registry)}"
        )
    return _registry[name](**kwargs)


def list_sources() -> list[str]:
    """Return all registered source names in sorted order.

    Returns
    -------
    list[str]
        Sorted list of registered adapter names.
    """
    return sorted(_registry)


__all__ = [
    "DataSource",
    "PatientData",
    "get_source",
    "list_sources",
    "register",
]
