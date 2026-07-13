from pathlib import Path

from models import oauth_state_nonces, users


def test_active_hh_model_and_migration() -> None:
    assert users.c.active_hh_account_id.nullable
    assert not oauth_state_nonces.c.expires_at.nullable
    migration = Path("src/migration/versions/20260712_0003_active_hh_account.py").read_text()
    assert 'down_revision = "20260711_0002"' in migration
    assert 'op.add_column("users"' in migration
    assert 'op.drop_column("users", "active_hh_account_id")' in migration
    assert '"oauth_state_nonces"' in migration
