"""
Shim for pkg_resources, which was removed from setuptools>=78.
Provides the subset of the API used by dellemc.powerscale:
  - parse_version  (delegates to packaging.version.Version)
  - working_set    (uses importlib.metadata to list installed packages)
"""

from packaging.version import Version as parse_version  # noqa: F401
import importlib.metadata


class _Distribution:
    """Minimal stand-in for pkg_resources.Distribution."""

    def __init__(self, meta):
        self.key = meta.metadata["Name"].lower()
        self.version = meta.version
        self.project_name = meta.metadata["Name"]

    def __repr__(self):
        return f"{self.project_name} {self.version}"


class _WorkingSet(list):
    """Minimal stand-in for pkg_resources.WorkingSet."""

    def __init__(self):
        super().__init__(
            _Distribution(d) for d in importlib.metadata.distributions()
        )


working_set = _WorkingSet()
