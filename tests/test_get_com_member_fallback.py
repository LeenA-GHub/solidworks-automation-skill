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
    then restores the original state after the module.
    
    Surgical isolation: tracks EXACTLY what it modifies and restores only that.
    """
    # Track EXACTLY what we modify - no broad sweeps
    sw_preflight_existed_before = "sw_preflight" in sys.modules
    orig_sw_preflight = sys.modules.get("sw_preflight")
    path_inserted = SCRIPTS_DIR not in sys.path
    
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

    if path_inserted:
        sys.path.insert(0, SCRIPTS_DIR)

    try:
        spec = importlib.util.spec_from_file_location(
            "sw_connect_under_test", os.path.join(SCRIPTS_DIR, "sw_connect.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module.get_com_member
    finally:
        # Surgical teardown: remove ONLY the module we created
        if "sw_connect_under_test" in sys.modules:
            del sys.modules["sw_connect_under_test"]
        
        # Restore sys.path only if we inserted it
        if path_inserted and SCRIPTS_DIR in sys.path:
            sys.path.remove(SCRIPTS_DIR)
        
        # Restore sw_preflight precisely
        if sw_preflight_existed_before and orig_sw_preflight is not None:
            sys.modules["sw_preflight"] = orig_sw_preflight
        elif not sw_preflight_existed_before and "sw_preflight" in sys.modules:
            del sys.modules["sw_preflight"]


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


class _RuntimeAttrRaiser:
    """A present, callable member that raises AttributeError when invoked."""

    def RaiseAttrError(self):
        raise AttributeError("member not found at runtime")


def test_attribute_error_during_invocation_with_default_propagates(get_com_member):
    """
    `default` must only cover the getattr LOOKUP miss.
    An AttributeError raised while CALLING a present member must propagate,
    even when a default is supplied.
    """
    with pytest.raises(AttributeError, match="member not found at runtime"):
        get_com_member(_RuntimeAttrRaiser(), "RaiseAttrError", default=None)


def test_callable_returns_none_is_not_treated_as_default_missing(get_com_member):
    """
    A callable that returns None must return None, NOT the default value.
    The default is only used when the attribute is missing entirely.
    """
    class _ReturnsNone:
        def GetValue(self):
            return None

    result = get_com_member(_ReturnsNone(), "GetValue", default="fallback")
    assert result is None


def test_missing_member_with_falsy_default_returns_falsy(get_com_member):
    """
    Falsy defaults (0, "", False, []) must be returned as-is when member is missing.
    The default logic must not treat falsy values as "no default provided".
    """
    obj = _Obj()
    assert get_com_member(obj, "NonExistent", default=0) == 0
    assert get_com_member(obj, "NonExistent", default="") == ""
    assert get_com_member(obj, "NonExistent", default=False) is False
    assert get_com_member(obj, "NonExistent", default=[]) == []


def test_present_member_with_falsy_default_ignores_default(get_com_member):
    """
    When the member exists, the default must be ignored entirely.
    Falsy defaults must not affect the return value of present members.
    """
    obj = _Obj()
    # Present attribute with falsy default
    assert get_com_member(obj, "color", default="blue") == "red"
    # Present callable with falsy default
    assert get_com_member(obj, "GetTitle", default=None) == "part1"
    assert get_com_member(obj, "Add", 2, 3, default=999) == 5