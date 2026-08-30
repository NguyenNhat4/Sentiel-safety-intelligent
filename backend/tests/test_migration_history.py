from alembic.config import Config
from alembic.script import ScriptDirectory


def test_legacy_head_is_a_descendant_of_the_current_tracking_revision() -> None:
    script = ScriptDirectory.from_config(Config("alembic.ini"))

    legacy_head = script.get_revision("20260825_03")

    assert legacy_head is not None
    assert legacy_head.down_revision == "20260825_01"
    assert list(script.get_heads()) == ["20260825_03"]
