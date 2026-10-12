import pytest

from adrin_sim.config import load_config, PROJECT_ROOT


def test_default_config_loads(cfg):
    assert cfg.simulation.n_nodes == 50
    assert cfg.simulation.duration_min == 200
    assert len(cfg.mobility.zones) == 5


def test_experiment_file_overrides_only_what_it_lists():
    exp = load_config(str(PROJECT_ROOT / "configs" / "experiments" / "example_fraction_50.yaml"))
    assert exp.sharing.policy == "fraction"
    assert exp.sharing.level == 0.5
    assert exp.simulation.n_nodes == 50          # untouched default


def test_missing_file_gives_clear_error():
    with pytest.raises(FileNotFoundError):
        load_config("configs/experiments/does_not_exist.yaml")


def test_bad_sharing_policy_is_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("sharing:\n  policy: banana\n  level: 0.5\n")
    with pytest.raises(ValueError):
        load_config(str(bad))


def test_planned_recent_policy_is_rejected_up_front(tmp_path):
    exp = tmp_path / "recent.yaml"
    exp.write_text("sharing:\n  policy: recent\n")
    with pytest.raises(ValueError, match="not implemented yet"):
        load_config(str(exp))


def test_bad_routing_settings_are_rejected(tmp_path):
    for text in ("network:\n  backtrack_power: cube\n", "network:\n  forwarding: flood\n",
                 "network:\n  model_smoothing: 0\n"):
        bad = tmp_path / "bad.yaml"
        bad.write_text(text)
        with pytest.raises(ValueError):
            load_config(str(bad))
