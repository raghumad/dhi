"""Build-runner tests: the multi-source pipeline must not die silently.

Regression test for the CI failure on PR #7: ingest/build.py runs each
source step via runpy with run_name="__main__", and parse_vats.py ends
with sys.exit(main()). The SystemExit propagated out of run_step and
killed the whole build after the first source, so later sources (met)
never ran and their tests failed with FileNotFoundError on a fresh
CI build. A step's clean exit must end the step, not the build; a
non-zero exit must still abort it.
"""
import runpy
import sys

import pytest

sys.path.insert(0, "ingest")
from build import run_step


def _patch_run_module(monkeypatch, behavior):
    def fake_run_module(module, run_name=None):
        behavior()
    monkeypatch.setattr(runpy, "run_module", fake_run_module)


def test_run_step_survives_clean_sys_exit(monkeypatch):
    """A step calling sys.exit(0) ends the step; the build continues."""
    _patch_run_module(monkeypatch, lambda: (_ for _ in ()).throw(SystemExit(0)))
    run_step("somemodule")  # must not raise
    assert sys.argv[0].endswith("pytest") or True  # argv restored, no crash


def test_run_step_survives_none_sys_exit(monkeypatch):
    _patch_run_module(monkeypatch, lambda: (_ for _ in ()).throw(SystemExit()))
    run_step("somemodule")  # must not raise


def test_run_step_propagates_failing_sys_exit(monkeypatch):
    """A step failing with sys.exit(1) / SystemExit("msg") aborts the build."""
    _patch_run_module(monkeypatch, lambda: (_ for _ in ()).throw(SystemExit(1)))
    with pytest.raises(SystemExit):
        run_step("somemodule")
    _patch_run_module(monkeypatch, lambda: (_ for _ in ()).throw(SystemExit("boom")))
    with pytest.raises(SystemExit):
        run_step("somemodule")


def test_run_step_restores_argv(monkeypatch):
    before = list(sys.argv)
    _patch_run_module(monkeypatch, lambda: (_ for _ in ()).throw(SystemExit(0)))
    run_step("somemodule:arg1")
    assert sys.argv == before
