import sys
import tarfile

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


def test_restore_extracts_expected_data_directory(tmp_path, monkeypatch):
    source = tmp_path / "source"
    (source / "data").mkdir(parents=True)
    (source / "data" / "events.db").write_text("restored", encoding="utf-8")
    archive = tmp_path / "data.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        handle.add(source / "data", arcname="data")
    target = tmp_path / "target" / "data"
    monkeypatch.setattr(sys, "argv", ["restore_data.py", str(archive), "--target-dir", str(target)])

    restore_data.main()

    assert (target / "events.db").read_text(encoding="utf-8") == "restored"


def test_restore_rejects_archive_outside_target_directory(tmp_path, monkeypatch):
    archive = tmp_path / "invalid.tar.gz"
    payload = tmp_path / "payload.txt"
    payload.write_text("bad", encoding="utf-8")
    with tarfile.open(archive, "w:gz") as handle:
        handle.add(payload, arcname="other/payload.txt")
    target = tmp_path / "data"
    monkeypatch.setattr(sys, "argv", ["restore_data.py", str(archive), "--target-dir", str(target)])

    with pytest.raises(SystemExit, match="unsafe or unexpected"):
        restore_data.main()
