import pytest
import tempfile
from pathlib import Path

from athena.core import ATHENA


@pytest.fixture
def tmp_garrison(tmp_path):
    return str(tmp_path / "test-garrison")


@pytest.fixture
def athena_instance(tmp_garrison):
    return ATHENA(
        garrison_path=tmp_garrison,
        core_mode="local",
        require_core=False,
        core_refresh_before_plan=False,
    )
