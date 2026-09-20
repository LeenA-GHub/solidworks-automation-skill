"""
Shared pytest fixtures for get_com_member tests (issue #16).

No SolidWorks and no pywin32 required. The get_com_member fixture stubs
sw_preflight temporarily during import, restoring sys.modules and sys.path
after the module. Placed in conftest.py so all test modules in tests/ share it
via pytest fixture discovery (no imports needed).
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
    # Track whether sw_connect_under_test existed BEFORE we create it
    sw_connect_under_test_existed_before = "sw_connect_under_test" in sys.modules
    orig_sw_connect_under_test = sys.modules.get("sw_connect_under_test")

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
        # Surgical teardown: restore sw_connect_under_test precisely
        if sw_connect_under_test_existed_before and orig_sw_connect_under_test is not None:
            sys.modules["sw_connect_under_test"] = orig_sw_connect_under_test
        elif not sw_connect_under_test_existed_before and "sw_connect_under_test" in sys.modules:
            del sys.modules["sw_connect_under_test"]

        # Restore sys.path only if we inserted it
        if path_inserted and SCRIPTS_DIR in sys.path:
            sys.path.remove(SCRIPTS_DIR)

        # Restore sw_preflight precisely
        if sw_preflight_existed_before and orig_sw_preflight is not None:
            sys.modules["sw_preflight"] = orig_sw_preflight
        elif not sw_preflight_existed_before and "sw_preflight" in sys.modules:
            del sys.modules["sw_preflight"]


@pytest.fixture
def fake_com_obj():
    """
    Shared fake COM object for get_com_member tests.
    Provides a mix of attributes and callables for testing.
    Used by test_get_com_member_core.py and test_get_com_member_edge_cases.py.
    """
    class _Obj:
        """A fake COM object with a mix of attributes and callables."""
        color = "red"

        def GetTitle(self):
            return "part1"

        def Add(self, a, b):
            return a + b

        def RaiseError(self):
            raise RuntimeError("COM error")

    return _Obj


@pytest.fixture(scope="module")
def sw_connect():
    """
    Import sw_connect module without needing Windows/pywin32.
    Provides access to _read_active_document for caller-level tests.
    
    Uses the same stubbing pattern as the get_com_member fixture.
    """
    # Track EXACTLY what we modify
    sw_preflight_existed_before = "sw_preflight" in sys.modules
    orig_sw_preflight = sys.modules.get("sw_preflight")
    path_inserted = SCRIPTS_DIR not in sys.path
    sw_connect_under_test_existed_before = "sw_connect_under_test" in sys.modules
    orig_sw_connect_under_test = sys.modules.get("sw_connect_under_test")

    # Stub sw_preflight so import_com_dependencies() returns harmless placeholders
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
        yield module
    finally:
        # Surgical teardown
        if sw_connect_under_test_existed_before and orig_sw_connect_under_test is not None:
            sys.modules["sw_connect_under_test"] = orig_sw_connect_under_test
        elif not sw_connect_under_test_existed_before and "sw_connect_under_test" in sys.modules:
            del sys.modules["sw_connect_under_test"]

        if path_inserted and SCRIPTS_DIR in sys.path:
            sys.path.remove(SCRIPTS_DIR)

        if sw_preflight_existed_before and orig_sw_preflight is not None:
            sys.modules["sw_preflight"] = orig_sw_preflight
        elif not sw_preflight_existed_before and "sw_preflight" in sys.modules:
            del sys.modules["sw_preflight"]