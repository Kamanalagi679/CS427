import pytest

from adrin_sim.config import load_config


@pytest.fixture
def cfg():
    return load_config()
