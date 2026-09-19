"""
Mocked unit test for get_com_member's `default` fallback (issue #16).

No SolidWorks and no pywin32 required. Uses a pytest fixture to stub
sw_preflight temporarily during import, restoring sys.modules and sys.path
after the test session.

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


@pytest.fixture(scope="module")
def get_com_member():
    """
    Import get_com_member without needing Windows/pywin32.
    Temporarily stubs sw_preflight so sw_connect imports cleanly on Linux/Docker,
    then restores the original sys.modules and sys.path after the module.
    """
    # Save original state
    orig_modules = set(sys.modules.keys())
    orig_path = list(sys.path)

    # Stub sw_preflight so import_com_dependencies() returns harmless placeholders
    # and ensure_solidworks_installed() is a no-op.
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

    try:
        spec = importlib.util.spec_from_file_location(
            "sw_connect_under_test", os.path.join(SCRIPTS_DIR, "sw_connect.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module.get_com_member
    finally:
        # Restore sys.modules and sys.path to avoid interfering with other tests
        sys.path[:] = orig_path
        for name in list(sys.modules.keys()):
            if name not in orig_modules:
                del sys.modules[name]


class _Obj:
    """A fake COM object with a mix of attributes and callables."""

    color = "red"                       # plain attribute

    def GetTitle(self):                 # callable, no args
        return "part1"

    def Add(self, a, b):                # callable, with args
        return a + b

    def RaiseError(self):               # callable that raises
        raise RuntimeError("COM error")


def test_missing_member_with_default_returns_default(get_com_member):
    """This FAILS on the old code (raises AttributeError), PASSES on the fixed code."""
    assert get_com_member(_Obj(), "GetFirstCenterMark2", default=None) is None
    assert get_com_member(_Obj(), "Nope", default=42) == 42


def test_missing_member_without_default_still_raises(get_com_member):
    """Backward compatibility: no default -> same behavior as before (raise)."""
    with pytest.raises(AttributeError):
        get_com_member(_Obj(), "GetFirstCenterMark2")


def test_present_attribute_returned_as_is(get_com_member):
    assert get_com_member(_Obj(), "color") == "red"


def test_present_callable_no_args_is_called(get_com_member):
    assert get_com_member(_Obj(), "GetTitle") == "part1"


def test_present_callable_with_args_is_called(get_com_member):
    assert get_com_member(_Obj(), "Add", 2, 3) == 5


def test_callable_error_propagates(get_com_member):
    """
    The fix only catches AttributeError on member lookup.
    Exceptions raised by CALLING the member must propagate unchanged.
    """
    with pytest.raises(RuntimeError, match="COM error"):
        get_com_member(_Obj(), "RaiseError")
