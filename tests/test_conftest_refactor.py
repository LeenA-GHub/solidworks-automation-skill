"""Verify refactored conftest.py fixtures work correctly."""
import sys
import pytest


def test_get_com_member_fixture_yields_callable(get_com_member):
    """Fixture yields the get_com_member function."""
    assert callable(get_com_member)


def test_get_com_member_basic_attr(get_com_member, fake_com_obj):
    """get_com_member reads simple attribute."""
    obj = fake_com_obj()
    result = get_com_member(obj, "color")
    assert result == "red"


def test_get_com_member_callable_no_args(get_com_member, fake_com_obj):
    """get_com_member calls zero-arg method."""
    obj = fake_com_obj()
    result = get_com_member(obj, "GetTitle")
    assert result == "part1"


def test_get_com_member_callable_with_args(get_com_member, fake_com_obj):
    """get_com_member calls method with arguments."""
    obj = fake_com_obj()
    result = get_com_member(obj, "Add", 2, 3)
    assert result == 5


def test_get_com_member_missing_attr_raises(get_com_member, fake_com_obj):
    """get_com_member raises AttributeError for missing member."""
    obj = fake_com_obj()
    with pytest.raises(AttributeError):
        get_com_member(obj, "nonexistent")


def test_get_com_member_missing_attr_with_default(get_com_member, fake_com_obj):
    """get_com_member returns default for missing member when default provided."""
    obj = fake_com_obj()
    result = get_com_member(obj, "nonexistent", default="fallback")
    assert result == "fallback"


def test_sw_connect_fixture_yields_module(sw_connect):
    """Fixture yields the sw_connect module."""
    assert hasattr(sw_connect, "get_com_member")
    assert hasattr(sw_connect, "_read_active_document")
    assert callable(sw_connect.get_com_member)


def test_sw_connect_module_isolation(sw_connect):
    """Module is imported as sw_connect_under_test, not polluting sys.modules."""
    # The fixture should have cleaned up after itself in the context manager
    # but during the test, sw_connect_under_test should exist
    assert "sw_connect_under_test" in sys.modules


def test_fake_com_obj_returns_class(fake_com_obj):
    """fake_com_obj fixture returns a class, not an instance."""
    assert isinstance(fake_com_obj, type)
    obj = fake_com_obj()
    assert obj.color == "red"
