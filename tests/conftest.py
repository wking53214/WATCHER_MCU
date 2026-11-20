"""Shared test setup.

Since 2026-11-19 `watcher narrate --out` refuses a record that names no governed folder
unless `--target` is given (`watcher.evidence.target_refusal`). The recorded fixtures are real
Warden records from before that field existed, and most tests are about something else (the
oath, the writing, the exit codes), so by default the tests that call `main` directly are told
a governed folder of their own. A test about the target rule calls `cli.main`, which is not
wrapped, or passes its own `--target`.
"""
import sys

import pytest

from watcher import cli


@pytest.fixture(autouse=True)
def _tell_main_a_governed_folder(request, tmp_path_factory, monkeypatch):
    module = request.module
    if getattr(module, "main", None) is not cli.main:
        yield
        return
    real = cli.main

    def main(argv=None, *rest, **options):
        args = list(sys.argv[1:] if argv is None else argv)
        if args[:1] == ["narrate"] and "--out" in args and "--target" not in args:
            folder = tmp_path_factory.mktemp("governed")
            args += ["--target", str(folder)]
        return real(args, *rest, **options)

    monkeypatch.setattr(module, "main", main)
    yield
