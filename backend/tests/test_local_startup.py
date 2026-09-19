from sqlalchemy import text

from app.core.config import BACKEND_DIR, Settings
from app.core.database import create_database_engine


def test_api_root_opens_docs(client):
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 307
    assert response.headers['location'] == 'docs'


def test_relative_sqlite_path_is_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine = create_database_engine(Settings(database_url='sqlite:///./data/community.db'))
    try:
        assert engine.url.database == str(BACKEND_DIR / 'data/community.db')
        with engine.connect() as connection:
            assert connection.execute(text('SELECT 1')).scalar() == 1
        assert not (tmp_path / 'data').exists()
    finally:
        engine.dispose()
