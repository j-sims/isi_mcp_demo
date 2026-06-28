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
        dists = []
        for d in importlib.metadata.distributions():
            try:
                # A distribution with incomplete .dist-info metadata can have a
                # missing "Name" (email.message returns None, so .lower() would
                # raise AttributeError). pkg_resources tolerated such packages —
                # skip the bad one rather than break the whole working_set (which
                # would, in turn, break the dellemc.powerscale import).
                dists.append(_Distribution(d))
            except Exception:
                continue
        super().__init__(dists)


working_set = _WorkingSet()
