"""@brief Verify FeatureCut4 parameter order in extrude_cut."""

import pytest
from scripts import sw_part


class FakeFeature:
    """@brief Mock SolidWorks Feature."""
    Name = ""


class FakeFeatureManager:
    """@brief Record FeatureCut4 arguments."""
    def __init__(self):
        self.cut_calls = []

    def FeatureCut4(self, *args):
        self.cut_calls.append(args)
        return FakeFeature()


class FakeModel:
    """@brief Minimal model interface for extrude_cut."""
    def __init__(self):
        self.FeatureManager = FakeFeatureManager()

    def ClearSelection2(self, clear_all):
        return True


def test_extrude_cut_sd_always_true(monkeypatch):
    """@brief Sd (arg0) must always be True regardless of direction."""
    model = FakeModel()
    monkeypatch.setattr(sw_part, "_ensure_sketch_selected", lambda *args: None)
    sw_part.extrude_cut(model, "Sketch1", 0.01, direction=True)
    args = model.FeatureManager.cut_calls[0]
    assert args[0] is True  # Sd


def test_extrude_cut_sd_true_even_when_direction_false(monkeypatch):
    """@brief Sd (arg0) must stay True even with direction=False.

    OLD buggy code put `direction` into Sd, so direction=False would fail.
    Fixed code hardcodes Sd=True, so this asserts the fix holds.
    """
    model = FakeModel()
    monkeypatch.setattr(sw_part, "_ensure_sketch_selected", lambda *args: None)
    sw_part.extrude_cut(model, "Sketch1", 0.01, direction=False)
    args = model.FeatureManager.cut_calls[0]
    assert args[0] is True  # Sd stays True (fix validated)
    assert args[2] is False  # Dir receives direction=False


def test_extrude_cut_flip_flows_true(monkeypatch):
    """@brief flip=True must flow into Flip (arg1)."""
    model = FakeModel()
    monkeypatch.setattr(sw_part, "_ensure_sketch_selected", lambda *args: None)
    sw_part.extrude_cut(model, "Sketch1", 0.01, flip=True)
    args = model.FeatureManager.cut_calls[0]
    assert args[1] is True  # Flip


def test_extrude_cut_flip_flows_false(monkeypatch):
    """@brief flip=False must flow into Flip (arg1)."""
    model = FakeModel()
    monkeypatch.setattr(sw_part, "_ensure_sketch_selected", lambda *args: None)
    sw_part.extrude_cut(model, "Sketch1", 0.01, flip=False)
    args = model.FeatureManager.cut_calls[0]
    assert args[1] is False  # Flip


def test_extrude_cut_dir_flows_true(monkeypatch):
    """@brief direction=True must flow into Dir (arg2)."""
    model = FakeModel()
    monkeypatch.setattr(sw_part, "_ensure_sketch_selected", lambda *args: None)
    sw_part.extrude_cut(model, "Sketch1", 0.01, direction=True)
    args = model.FeatureManager.cut_calls[0]
    assert args[2] is True  # Dir


def test_extrude_cut_dir_flows_false(monkeypatch):
    """@brief direction=False must flow into Dir (arg2)."""
    model = FakeModel()
    monkeypatch.setattr(sw_part, "_ensure_sketch_selected", lambda *args: None)
    sw_part.extrude_cut(model, "Sketch1", 0.01, direction=False)
    args = model.FeatureManager.cut_calls[0]
    assert args[2] is False  # Dir


def test_extrude_cut_end_condition_when_depth_zero(monkeypatch):
    """@brief depth=0 must set end_condition to 1 (Through All)."""
    model = FakeModel()
    monkeypatch.setattr(sw_part, "_ensure_sketch_selected", lambda *args: None)
    sw_part.extrude_cut(model, "Sketch1", 0, direction=True)
    args = model.FeatureManager.cut_calls[0]
    assert args[3] == 1  # end_condition = swEndCondThroughAll


def test_extrude_cut_assembly_scope_flags_false(monkeypatch):
    """@brief Assembly-scope flags (args 20-21) must be False for part docs."""
    model = FakeModel()
    monkeypatch.setattr(sw_part, "_ensure_sketch_selected", lambda *args: None)
    sw_part.extrude_cut(model, "Sketch1", 0.01, direction=True)
    args = model.FeatureManager.cut_calls[0]
    assert args[19] is True   # UseAutoSelect
    assert args[20] is False  # AssemblyFeatureScope
    assert args[21] is False  # AutoSelectComponents
