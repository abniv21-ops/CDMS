import pytest
from app import create_app
from app.extensions import db
from app.models import User, Document, Compartment


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    user = User(
        username='testadmin',
        email='admin@test.com',
        role='admin',
        clearance_level=3,
        is_active=True,
    )
    user.set_password('TestPass123!')
    db.session.add(user)
    db.session.commit()
    return user.id


@pytest.fixture
def viewer_user(app):
    user = User(
        username='testviewer',
        email='viewer@test.com',
        role='viewer',
        clearance_level=0,
        is_active=True,
    )
    user.set_password('TestPass123!')
    db.session.add(user)
    db.session.commit()
    return user.id


def login(client, username, password):
    return client.post('/auth/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=True)


class TestAuth:
    def test_login_page_loads(self, client):
        rv = client.get('/auth/login')
        assert rv.status_code == 200
        assert b'Sign In' in rv.data

    def test_register_page_loads(self, client):
        rv = client.get('/auth/register')
        assert rv.status_code == 200
        assert b'Register' in rv.data

    def test_login_success(self, client, admin_user):
        rv = login(client, 'testadmin', 'TestPass123!')
        assert rv.status_code == 200

    def test_login_failure(self, client, admin_user):
        rv = login(client, 'testadmin', 'wrongpassword')
        assert b'Invalid username or password' in rv.data

    def test_logout(self, client, admin_user):
        login(client, 'testadmin', 'TestPass123!')
        rv = client.get('/auth/logout', follow_redirects=True)
        assert b'logged out' in rv.data.lower()


class TestAccessControl:
    def test_clearance_blocks_access(self, app, viewer_user):
        """Viewer with UNCLASSIFIED clearance should not access SECRET docs."""
        user = db.session.get(User, viewer_user)
        doc = Document(
            title='Secret Doc',
            classification_level=2,
            file_path='/fake/path',
            file_name='test.pdf',
            author_id=user.id,
        )
        assert not user.can_access_document(doc)

    def test_clearance_allows_access(self, app, admin_user):
        """Admin with TOP SECRET clearance should access SECRET docs."""
        user = db.session.get(User, admin_user)
        doc = Document(
            title='Secret Doc',
            classification_level=2,
            file_path='/fake/path',
            file_name='test.pdf',
            author_id=user.id,
        )
        assert user.can_access_document(doc)

    def test_compartment_blocks_access(self, app, admin_user):
        """User without required compartment should be blocked."""
        user = db.session.get(User, admin_user)
        comp = Compartment(name='TEST_SCI', display_name='Test SCI', description='Test')
        db.session.add(comp)
        db.session.flush()

        doc = Document(
            title='Compartmented Doc',
            classification_level=3,
            file_path='/fake/path',
            file_name='test.pdf',
            author_id=user.id,
        )
        doc.compartments = [comp]
        assert not user.can_access_document(doc)


class TestAuditChain:
    def test_audit_log_integrity(self, app):
        """Verify audit hash chain after logging actions."""
        with app.app_context():
            from app.audit.services import log_action, verify_audit_chain

            log_action('test_action_1', resource_type='test', details={'key': 'val1'})
            log_action('test_action_2', resource_type='test', details={'key': 'val2'})
            log_action('test_action_3', resource_type='test', details={'key': 'val3'})

            is_valid, total, errors = verify_audit_chain()
            assert is_valid
            assert total == 3
            assert len(errors) == 0
