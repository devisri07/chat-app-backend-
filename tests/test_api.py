"""Backend unit and integration tests."""
import pytest
from app import create_app, db
from app.models import User, Channel, Message, ChannelMembership, RefreshToken
import json
from datetime import datetime


@pytest.fixture
def app():
    """Create app with test database."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Flask CLI runner."""
    return app.test_cli_runner()


class TestAuth:
    """Auth endpoint tests."""
    
    def test_signup_success(self, client):
        """Test successful signup."""
        response = client.post('/api/auth/signup', json={
            'display_name': 'Alice',
            'password': 'SecurePassword123'
        })
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'access_token' in data
        assert 'user' in data
        assert data['user']['display_name'] == 'Alice'
    
    def test_signup_duplicate_name(self, client):
        """Test signup with duplicate display name."""
        client.post('/api/auth/signup', json={
            'display_name': 'Alice',
            'password': 'SecurePassword123'
        })
        response = client.post('/api/auth/signup', json={
            'display_name': 'Alice',
            'password': 'AnotherPassword123'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_login_success(self, client):
        """Test successful login."""
        client.post('/api/auth/signup', json={
            'display_name': 'Alice',
            'password': 'SecurePassword123'
        })
        response = client.post('/api/auth/login', json={
            'display_name': 'Alice',
            'password': 'SecurePassword123'
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'access_token' in data
    
    def test_login_invalid_password(self, client):
        """Test login with wrong password."""
        client.post('/api/auth/signup', json={
            'display_name': 'Alice',
            'password': 'SecurePassword123'
        })
        response = client.post('/api/auth/login', json={
            'display_name': 'Alice',
            'password': 'WrongPassword'
        })
        assert response.status_code == 401
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post('/api/auth/login', json={
            'display_name': 'NonExistent',
            'password': 'SomePassword'
        })
        assert response.status_code == 401


class TestChannels:
    """Channel endpoint tests."""
    
    def test_list_channels_unauthorized(self, client):
        """Test listing channels without auth."""
        response = client.get('/api/channels')
        assert response.status_code == 401
    
    def test_list_channels_authorized(self, client, app):
        """Test listing channels with auth."""
        # Create user and get token
        signup_resp = client.post('/api/auth/signup', json={
            'display_name': 'Alice',
            'password': 'SecurePassword123'
        })
        token = json.loads(signup_resp.data)['access_token']
        
        # Add authorization header
        headers = {'Authorization': f'Bearer {token}'}
        response = client.get('/api/channels', headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'channels' in data
        assert isinstance(data['channels'], list)
    
    def test_create_channel_success(self, client):
        """Test successful channel creation."""
        # Signup
        signup_resp = client.post('/api/auth/signup', json={
            'display_name': 'Alice',
            'password': 'SecurePassword123'
        })
        token = json.loads(signup_resp.data)['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # Create channel
        response = client.post('/api/channels', json={
            'name': 'general',
            'description': 'General chat',
            'is_private': False
        }, headers=headers)
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['channel']['name'] == 'general'
    
    def test_join_channel_success(self, client, app):
        """Test joining a public channel."""
        # Create two users
        signup1 = client.post('/api/auth/signup', json={
            'display_name': 'Alice',
            'password': 'SecurePassword123'
        })
        token1 = json.loads(signup1.data)['access_token']
        user1_id = json.loads(signup1.data)['user']['id']
        
        signup2 = client.post('/api/auth/signup', json={
            'display_name': 'Bob',
            'password': 'SecurePassword456'
        })
        token2 = json.loads(signup2.data)['access_token']
        
        # Alice creates channel
        create_resp = client.post('/api/channels', json={
            'name': 'general',
            'is_private': False
        }, headers={'Authorization': f'Bearer {token1}'})
        channel_id = json.loads(create_resp.data)['channel']['id']
        
        # Bob joins channel
        response = client.post(f'/api/channels/{channel_id}/join', 
                             headers={'Authorization': f'Bearer {token2}'})
        assert response.status_code == 200


class TestMessages:
    """Message endpoint tests."""
    
    def test_get_messages_unauthorized(self, client, app):
        """Test getting messages without auth."""
        with app.app_context():
            channel = Channel(name='test', description='test')
            db.session.add(channel)
            db.session.commit()
            channel_id = channel.id
        
        response = client.get(f'/api/channels/{channel_id}/messages')
        assert response.status_code == 401
    
    def test_get_messages_success(self, client, app):
        """Test getting messages from joined channel."""
        # Create user and channel
        signup = client.post('/api/auth/signup', json={
            'display_name': 'Alice',
            'password': 'SecurePassword123'
        })
        token = json.loads(signup.data)['access_token']
        user_id = json.loads(signup.data)['user']['id']
        
        create_resp = client.post('/api/channels', json={
            'name': 'general',
            'is_private': False
        }, headers={'Authorization': f'Bearer {token}'})
        channel_id = json.loads(create_resp.data)['channel']['id']
        
        # Get messages
        response = client.get(f'/api/channels/{channel_id}/messages',
                            headers={'Authorization': f'Bearer {token}'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'messages' in data
        assert 'next_cursor' in data
        assert 'has_more' in data


class TestHealth:
    """Health check tests."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/healthz')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
