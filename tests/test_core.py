from datetime import datetime

from athena.core import ATHENA
from athena.types import Component, MissionStatus, Priority
from athena.olympians.base import Olympian


def test_athena_init(athena_instance):
    assert athena_instance.mission_status == MissionStatus.RECEIVED
    assert athena_instance.current_objective is None
    assert athena_instance.current_plan is None
    assert len(athena_instance.olympians) == 0


def test_athena_local_core(athena_instance):
    assert athena_instance.core_client is not None
    health = athena_instance.core_client.health_check()
    assert health["status"] == "ok"
    assert health["mode"] == "local"


def test_register_olympian(athena_instance):
    olympian = Olympian(name="TEST", domain="Testing")
    athena_instance.register_olympian(olympian)
    assert "TEST" in athena_instance.olympians
    assert athena_instance.olympians["TEST"].domain == "Testing"


def test_deploy_olympian(athena_instance):
    olympian = Olympian(name="TEST", domain="Testing")
    athena_instance.register_olympian(olympian)
    comp = Component(name="test_comp", type="testing", priority=1)
    result = athena_instance.deploy_olympian("TEST", comp)
    assert result is False  # No titans registered


def test_deploy_olympian_not_found(athena_instance):
    comp = Component(name="test_comp", type="testing", priority=1)
    result = athena_instance.deploy_olympian("NONEXISTENT", comp)
    assert result is False


def test_recall_olympian(athena_instance):
    olympian = Olympian(name="TEST", domain="Testing")
    athena_instance.register_olympian(olympian)
    athena_instance.recall_olympian("TEST")
    assert athena_instance.olympians["TEST"].status.value == "RETURNING"


def test_receive_objective(athena_instance):
    olympian = Olympian(name="ARES", domain="Backend Warfare")
    athena_instance.register_olympian(olympian)

    mission_id = athena_instance.receive_objective(
        description="Build an API service",
        deadline=datetime(2026, 3, 1),
        priority=Priority.HIGH,
    )
    assert mission_id.startswith("ATHENA-")
    assert athena_instance.current_objective is not None
    assert athena_instance.current_plan is not None


def test_generate_sitrep_standby(athena_instance):
    sitrep = athena_instance.generate_sitrep()
    assert "ATHENA SITUATION REPORT" in sitrep
    assert "STANDBY" in sitrep


def test_generate_sitrep_active(athena_instance):
    olympian = Olympian(name="ARES", domain="Backend Warfare")
    athena_instance.register_olympian(olympian)
    athena_instance.receive_objective(
        description="Build test service",
        deadline=datetime(2026, 3, 1),
    )
    sitrep = athena_instance.generate_sitrep()
    assert "Build test service" in sitrep


def test_complete_mission_no_objective(athena_instance):
    result = athena_instance.complete_mission()
    assert result is None


def test_knowledge_base_persistence(athena_instance):
    athena_instance.knowledge_base["test_key"] = "test_value"
    athena_instance._save_knowledge_base()

    reloaded = athena_instance._load_knowledge_base()
    assert reloaded["test_key"] == "test_value"
