from pathlib import Path
from types import SimpleNamespace

from open_webui.hermes_bridge import hermes_adapter as ha


def _completed(returncode=0):
    return SimpleNamespace(returncode=returncode, stdout="", stderr="")


def test_rollback_resets_the_active_engine_and_checks_health(monkeypatch, tmp_path):
    active = tmp_path / "active-hermes"
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return _completed()

    monkeypatch.setattr(ha, "_HERMES_CLONE", active)
    monkeypatch.setattr(ha.subprocess, "run", fake_run)
    monkeypatch.setattr(ha, "_restart_gateway", lambda: None)
    monkeypatch.setattr(ha, "_git_head", lambda: "before-update")
    monkeypatch.setattr(ha, "_engine_ready", lambda: True)

    assert ha._rollback("before-update", None) is True
    assert ["git", "-C", str(active), "reset", "--hard", "before-update"] in calls


def test_rollback_never_claims_success_when_commit_does_not_match(monkeypatch, tmp_path):
    monkeypatch.setattr(ha, "_HERMES_CLONE", tmp_path / "active-hermes")
    monkeypatch.setattr(ha.subprocess, "run", lambda *args, **kwargs: _completed())
    monkeypatch.setattr(ha, "_restart_gateway", lambda: None)
    monkeypatch.setattr(ha, "_git_head", lambda: "wrong-commit")
    monkeypatch.setattr(ha, "_engine_ready", lambda: True)

    assert ha._rollback("before-update", None) is False


def test_rollback_never_claims_success_when_engine_stays_offline(monkeypatch, tmp_path):
    monkeypatch.setattr(ha, "_HERMES_CLONE", tmp_path / "active-hermes")
    monkeypatch.setattr(ha.subprocess, "run", lambda *args, **kwargs: _completed())
    monkeypatch.setattr(ha, "_restart_gateway", lambda: None)
    monkeypatch.setattr(ha, "_git_head", lambda: "before-update")
    monkeypatch.setattr(ha, "_engine_ready", lambda: False)
    monkeypatch.setattr(ha.time, "sleep", lambda _seconds: None)

    assert ha._rollback("before-update", None) is False


def test_detached_seed_is_put_on_main_before_update(monkeypatch, tmp_path):
    active = tmp_path / "active-hermes"
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if "symbolic-ref" in argv:
            return _completed(returncode=1)
        return _completed()

    monkeypatch.setattr(ha, "_HERMES_CLONE", active)
    monkeypatch.setattr(ha.subprocess, "run", fake_run)

    assert ha._prepare_git_branch_for_update("pinned-commit") is True
    assert ["git", "-C", str(active), "checkout", "-B", "main", "pinned-commit"] in calls


def test_existing_branch_is_left_untouched(monkeypatch, tmp_path):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return _completed()

    monkeypatch.setattr(ha, "_HERMES_CLONE", tmp_path / "active-hermes")
    monkeypatch.setattr(ha.subprocess, "run", fake_run)

    assert ha._prepare_git_branch_for_update("current-commit") is True
    assert len(calls) == 1
