import tempfile
import sqlite3
from pathlib import Path
import database.db as db
from services.auth_service import hash_password, verify_password, register_farmer, login_farmer


def test_database_and_auth(monkeypatch):
    monkeypatch.setattr(db, 'DATABASE_PATH', Path(tempfile.mkdtemp())/'test.db')
    db.initialize_database()
    assert verify_password('secret12', hash_password('secret12'))
    assert register_farmer('Farmer','farmer','secret12','English')[0]
    assert not register_farmer('Farmer','farmer','secret12','English')[0]
    assert login_farmer('farmer','secret12')['name']=='Farmer'


def test_chat_exchange_is_atomic_and_validates_session_owner(monkeypatch):
    test_path = Path(tempfile.mkdtemp()) / 'chat.db'
    monkeypatch.setattr(db, 'DATABASE_PATH', test_path)
    db.initialize_database()
    first_user = db.execute(
        'INSERT INTO users(name,username,password_hash,language) VALUES(?,?,?,?)',
        ('First', 'first', 'hash', 'English'),
    )
    second_user = db.execute(
        'INSERT INTO users(name,username,password_hash,language) VALUES(?,?,?,?)',
        ('Second', 'second', 'hash', 'English'),
    )

    first_session = db.save_chat_exchange(
        first_user, None, 'Watering', 'How much water?', 'Check soil moisture.'
    )
    second_session = db.save_chat_exchange(
        second_user, first_session, 'Pests', 'What pest is this?', 'Inspect the leaf.'
    )

    assert second_session != first_session
    sessions = db.fetch_chat_sessions(second_user)
    assert sessions[0]['session_id'] == second_session
    messages = db.fetch_chat_messages(second_session)
    assert [(item['role'], item['message']) for item in messages] == [
        ('user', 'What pest is this?'),
        ('assistant', 'Inspect the leaf.'),
    ]


def test_chat_history_is_stored_in_the_main_database(monkeypatch):
    """Chat, disease and greenhouse data must all live in ONE database file."""
    test_path = Path(tempfile.mkdtemp()) / 'one.db'
    monkeypatch.setattr(db, 'DATABASE_PATH', test_path)
    db.initialize_database()
    user_id = db.execute(
        'INSERT INTO users(name,username,password_hash,language) VALUES(?,?,?,?)',
        ('One', 'one', 'hash', 'English'),
    )
    session_id = db.save_chat_exchange(user_id, None, 'T', 'Question', 'Answer')

    raw = sqlite3.connect(test_path)
    try:
        rows = raw.execute(
            'SELECT role,message FROM chat_messages WHERE session_id=? ORDER BY message_id',
            (session_id,),
        ).fetchall()
    finally:
        raw.close()
    assert rows == [('user', 'Question'), ('assistant', 'Answer')]
    assert not test_path.with_name('one_chat.db').exists()


def _make_legacy_chat_file(path, rows_sessions, rows_messages):
    legacy = sqlite3.connect(path)
    legacy.executescript(
        """
        CREATE TABLE chat_sessions(session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, title TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE chat_messages(message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL, role TEXT NOT NULL, message TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
        """
    )
    legacy.executemany(
        'INSERT INTO chat_sessions(session_id,user_id,title) VALUES(?,?,?)', rows_sessions)
    legacy.executemany(
        'INSERT INTO chat_messages(session_id,role,message) VALUES(?,?,?)', rows_messages)
    legacy.commit()
    legacy.close()


def test_legacy_chat_file_is_imported_once_and_never_modified(monkeypatch):
    directory = Path(tempfile.mkdtemp())
    test_path = directory / 'legacy.db'
    monkeypatch.setattr(db, 'DATABASE_PATH', test_path)
    db.initialize_database()
    user_id = db.execute(
        'INSERT INTO users(name,username,password_hash,language) VALUES(?,?,?,?)',
        ('Legacy', 'legacy', 'hash', 'English'),
    )
    legacy_file = directory / 'legacy_chat.db'
    # Session 1 belongs to the existing farmer; session 2 to a farmer (id 99)
    # that is not in `users` any more.
    _make_legacy_chat_file(
        legacy_file,
        [(1, user_id, 'Old chat'), (2, 99, 'Stranger chat')],
        [(1, 'user', 'Old question'), (1, 'assistant', 'Old answer'), (2, 'user', 'Not mine')],
    )
    before = legacy_file.read_bytes()

    db._INITIALIZED_DATABASES.clear()
    db.initialize_database()

    assert db.fetch_chat_sessions(user_id)[0]['title'] == 'Old chat'
    assert [m['message'] for m in db.fetch_chat_messages(1)] == ['Old question', 'Old answer']
    # The stranger's chat is not imported, so a newly registered farmer with
    # that id can never see it.
    assert db.fetch_one('SELECT 1 FROM chat_sessions WHERE session_id=2') is None
    assert db.get_admin_counts()['advisory_interactions'] == 1
    assert legacy_file.read_bytes() == before

    # A chat the farmer deletes afterwards must not come back on restart.
    assert db.delete_chat_session(user_id, 1)
    db._INITIALIZED_DATABASES.clear()
    db.initialize_database()
    assert db.fetch_chat_sessions(user_id) == []
