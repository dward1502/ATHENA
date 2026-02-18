from datetime import datetime

from athena.types import (
    BattlePlan,
    Component,
    DivisionStatus,
    Intel,
    MissionReport,
    MissionStatus,
    Objective,
    Priority,
)


def test_priority_values():
    assert Priority.ROUTINE.value == 1
    assert Priority.NORMAL.value == 2
    assert Priority.HIGH.value == 3
    assert Priority.CRITICAL.value == 4
    assert Priority.EMERGENCY.value == 5


def test_mission_status_values():
    assert MissionStatus.RECEIVED.value == "RECEIVED"
    assert MissionStatus.ANALYZING.value == "ANALYZING"
    assert MissionStatus.COMPLETE.value == "COMPLETE"


def test_division_status_values():
    assert DivisionStatus.STANDBY.value == "STANDBY"
    assert DivisionStatus.ACTIVE.value == "ACTIVE"
    assert DivisionStatus.RETURNING.value == "RETURNING"


def test_objective_to_dict():
    obj = Objective(
        description="Test mission",
        deadline=datetime(2026, 3, 1),
        priority=Priority.HIGH,
    )
    d = obj.to_dict()
    assert d["description"] == "Test mission"
    assert d["priority"] == "HIGH"
    assert "received_at" in d


def test_component_to_dict():
    comp = Component(name="test_comp", type="backend", priority=1)
    d = comp.to_dict()
    assert d["name"] == "test_comp"
    assert d["type"] == "backend"
    assert d["priority"] == 1
    assert d["status"] == "PENDING"
    assert d["progress"] == 0.0


def test_intel_to_dict():
    intel = Intel(
        source="APOLLO",
        timestamp=datetime(2026, 2, 17),
        message="Test intel",
        severity="WARNING",
    )
    d = intel.to_dict()
    assert d["source"] == "APOLLO"
    assert d["severity"] == "WARNING"


def test_battle_plan_to_dict():
    obj = Objective(
        description="Plan test",
        deadline=datetime(2026, 3, 1),
        priority=Priority.NORMAL,
    )
    comps = [Component(name="c1", type="api", priority=1)]
    plan = BattlePlan(
        objective=obj,
        components=comps,
        olympians_required=["ARES"],
        estimated_duration=4.0,
        risk_assessment="LOW",
    )
    d = plan.to_dict()
    assert d["olympians_required"] == ["ARES"]
    assert d["estimated_duration"] == 4.0
    assert len(d["components"]) == 1


def test_mission_report_to_dict():
    obj = Objective(
        description="Report test",
        deadline=datetime(2026, 3, 1),
        priority=Priority.CRITICAL,
    )
    report = MissionReport(
        objective=obj,
        status=MissionStatus.COMPLETE,
        components_completed=[],
        duration=1.5,
        resources_used={"olympians": 3},
        lessons_learned=["test lesson"],
    )
    d = report.to_dict()
    assert d["status"] == "COMPLETE"
    assert d["duration"] == 1.5
    assert d["lessons_learned"] == ["test lesson"]
