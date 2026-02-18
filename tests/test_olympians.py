from athena.types import Component, DivisionStatus
from athena.olympians.base import Olympian, Titan, TitanReport
from athena.olympians.apollo import APOLLO_OLYMPIAN
from athena.olympians.ares import ARES_OLYMPIAN
from athena.olympians.artemis import ARTEMIS_OLYMPIAN
from athena.olympians.hermes import HERMES_OLYMPIAN
from athena.olympians.hephaestus import HEPHAESTUS_OLYMPIAN, ExecutableTitan


def test_titan_deploy():
    titan = Titan("TEST_TITAN", "Test Specialty")
    comp = Component(name="test", type="backend", priority=1)
    report = titan.deploy(comp)
    assert isinstance(report, TitanReport)
    assert report.titan_name == "TEST_TITAN"
    assert report.status == "DEPLOYED"
    assert titan.status == "ACTIVE"


def test_titan_get_status():
    titan = Titan("T1", "Spec")
    status = titan.get_status()
    assert status["name"] == "T1"
    assert status["status"] == "STANDBY"
    assert status["current_task"] is None


def test_olympian_base():
    olympian = Olympian("TEST_OLY", "Test Domain")
    assert olympian.status == DivisionStatus.STANDBY
    assert olympian.missions_completed == 0


def test_olympian_deploy_no_titans():
    olympian = Olympian("TEST_OLY", "Test Domain")
    comp = Component(name="test", type="backend", priority=1)
    result = olympian.deploy(comp)
    assert result is False


def test_olympian_deploy_with_titan():
    olympian = Olympian("TEST_OLY", "Test Domain")
    titan = Titan("T1", "Spec")
    olympian.titans = [titan]
    comp = Component(name="test", type="backend", priority=1)
    result = olympian.deploy(comp)
    assert result is True
    assert olympian.status == DivisionStatus.ACTIVE
    assert comp.status == "IN_PROGRESS"


def test_olympian_cease_operations():
    olympian = Olympian("TEST_OLY", "Test Domain")
    titan = Titan("T1", "Spec")
    olympian.titans = [titan]
    comp = Component(name="test", type="backend", priority=1)
    olympian.deploy(comp)
    olympian.cease_operations()
    assert olympian.status == DivisionStatus.RETURNING
    assert titan.status == "STANDBY"
    assert olympian.current_mission is None


def test_olympian_report_intel():
    olympian = Olympian("TEST_OLY", "Test Domain")
    intel = olympian.report_intel("Test message", "WARNING")
    assert intel.message == "Test message"
    assert intel.severity == "WARNING"
    assert len(olympian.intel_stream) == 1


def test_apollo_init():
    apollo = APOLLO_OLYMPIAN()
    assert apollo.name == "APOLLO"
    assert apollo.domain == "Frontend & Creative"
    assert len(apollo.titans) == 9


def test_apollo_deploy_voice():
    apollo = APOLLO_OLYMPIAN()
    comp = Component(name="voice_interface", type="audio", priority=1)
    result = apollo.deploy(comp)
    assert result is True
    assert apollo.status == DivisionStatus.ACTIVE


def test_ares_init():
    ares = ARES_OLYMPIAN()
    assert ares.name == "ARES"
    assert ares.domain == "Backend Warfare"
    assert len(ares.titans) == 6


def test_ares_deploy_api():
    ares = ARES_OLYMPIAN()
    comp = Component(name="api_endpoint", type="api", priority=1)
    result = ares.deploy(comp)
    assert result is True


def test_artemis_init():
    artemis = ARTEMIS_OLYMPIAN()
    assert artemis.name == "ARTEMIS"
    assert artemis.domain == "Testing & Quality"
    assert len(artemis.titans) == 7


def test_artemis_deploy():
    artemis = ARTEMIS_OLYMPIAN()
    comp = Component(name="validation_suite", type="testing", priority=1)
    result = artemis.deploy(comp)
    assert result is True
    assert comp.status == "VALIDATED"
    assert artemis.tests_executed > 0


def test_hermes_init():
    hermes = HERMES_OLYMPIAN()
    assert hermes.name == "HERMES"
    assert hermes.domain == "Communications & Integration"
    assert len(hermes.titans) == 3


def test_hermes_deploy():
    hermes = HERMES_OLYMPIAN()
    comp = Component(name="webhook_handler", type="api", priority=1)
    result = hermes.deploy(comp)
    assert result is True


def test_hephaestus_init():
    heph = HEPHAESTUS_OLYMPIAN()
    assert heph.name == "HEPHAESTUS"
    assert heph.domain == "Infrastructure & Forge"
    assert len(heph.titans) == 3


def test_executable_titan():
    titan = ExecutableTitan("ET1", "Test")
    result = titan.run_stage(
        command=["python", "--version"],
        workdir=__import__("pathlib").Path.cwd(),
    )
    assert result["exit_code"] == 0
    assert "Python" in result["stdout"] or "Python" in result.get("stderr", "")
