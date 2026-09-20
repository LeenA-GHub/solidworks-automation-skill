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


def test_extrude_cut_passes_true_false_direction_for_direction_true(monkeypatch):
    """@brief direction=True must flow into Dir (3rd arg), not Sd."""
    model = FakeModel()
    monkeypatch.setattr(sw_part, "_ensure_sketch_selected", lambda *args: None)

    sw_part.extrude_cut(model, "Sketch1", 0.01, direction=True)

    args = model.FeatureManager.cut_calls[0]
    assert args[0] is True   # Sd
    assert args[1] is False  # Flip
    assert args[2] is True   # Dir = direction
    assert args[3] == 0      # end_condition (blind)
    assert args[4] == 0      # T2


def test_extrude_cut_passes_true_false_direction_for_direction_false(monkeypatch):
    """@brief direction=False must flow into Dir (3rd arg), proving the fix."""
    model = FakeModel()
    monkeypatch.setattr(sw_part, "_ensure_sketch_selected", lambda *args: None)

    sw_part.extrude_cut(model, "Sketch1", 0.01, direction=False)

    args = model.FeatureManager.cut_calls[0]
    assert args[0] is True   # Sd (always True)
    assert args[1] is False  # Flip (always False)
    assert args[2] is False  # Dir = direction (the key assertion)
    assert args[3] == 0      # end_condition
    assert args[4] == 0      # T2


def test_extrude_cut_uses_through_all_when_depth_zero(monkeypatch):
    """@brief depth=0 must set end_condition to 1 (Through All)."""
    model = FakeModel()
    monkeypatch.setattr(sw_part, "_ensure_sketch_selected", lambda *args: None)

    sw_part.extrude_cut(model, "Sketch1", 0, direction=True)

    args = model.FeatureManager.cut_calls[0]
    assert args[0] is True   # Sd
    assert args[1] is False  # Flip
    assert args[2] is True   # Dir
    assert args[3] == 1      # end_condition = swEndCondThroughAll
