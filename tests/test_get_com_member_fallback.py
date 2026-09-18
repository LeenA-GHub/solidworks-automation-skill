"""
Mocked unit test for get_com_member's `default` fallback (issue #16).

No SolidWorks and no pywin32 required. The production module
scripts/sw_connect.py imports COM dependencies at import time via
sw_preflight.import_com_dependencies(). Off-Windows that may raise, so this
test imports the module defensively: it stubs the COM dependency layer before
importing, and falls back to loading the single function from source if needed.

Place this file at: <repo>/tests/test_get_com_member_fallback.py
Run:  pytest -q tests/test_get_com_member_fallback.py
"""
import os
import sys
import types
import importlib.util

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")


def _load_get_com_member():
    """Import get_com_member without needing Windows/pywin32."""
    # Stub sw_preflight so import_com_dependencies() returns harmless placeholders
    # and ensure_solidworks_installed() is a no-op. This lets sw_connect import
    # cleanly on Linux inside the Docker container.
    stub = types.ModuleType("sw_preflight")

    def _import_com_dependencies():
        return (object(), object(), object())  # pythoncom, win32com_client, VARIANT

    def _ensure_solidworks_installed():
        return None

    stub.import_com_dependencies = _import_com_dependencies
    stub.ensure_solidworks_installed = _ensure_solidworks_installed
    sys.modules["sw_preflight"] = stub

    if SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, SCRIPTS_DIR)

    spec = importlib.util.spec_from_file_location(
        "sw_connect_under_test", os.path.join(SCRIPTS_DIR, "sw_connect.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.get_com_member


get_com_member = _load_get_com_member()


class _Obj:
    """A fake COM object with a mix of attributes and callables."""

    color = "red"                       # plain attribute

    def GetTitle(self):                 # callable, no args
        return "part1"

    def Add(self, a, b):                # callable, with args
        return a + b


def test_missing_member_with_default_returns_default():
    # assertion 1: this FAILS on the old code (raises AttributeError),
    # PASSES on the fixed code.
    assert get_com_member(_Obj(), "GetFirstCenterMark2", default=None) is None
    assert get_com_member(_Obj(), "Nope", default=42) == 42


def test_missing_member_without_default_still_raises():
    # backward compatibility: no default -> same behavior as before (raise).
    with pytest.raises(AttributeError):
        get_com_member(_Obj(), "GetFirstCenterMark2")


def test_present_attribute_returned_as_is():
    assert get_com_member(_Obj(), "color") == "red"


def test_present_callable_no_args_is_called():
    assert get_com_member(_Obj(), "GetTitle") == "part1"


def test_present_callable_with_args_is_called():
    assert get_com_member(_Obj(), "Add", 2, 3) == 5
