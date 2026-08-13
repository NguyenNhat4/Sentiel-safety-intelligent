import sys

import pytest

from scripts import restore_data


def test_restore_rejects_missing_archive(tmp_path, monkeypatch):
    archive = tmp_path / "missing.tar.gz"
    target = tmp_path / "data"
    target.mkdir()
    (target / "events.db").write_text("existing", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["restore_data.py", str(archive), "--target-dir", str(target)])

    with pytest.raises(SystemExit, match="Archive does not exist"):
        restore_data.main()
