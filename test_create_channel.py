#!/usr/bin/env python
"""Test create channel endpoint."""

from app import create_app, db
from app.models import User
from app.routes.auth import create_access_token
import uuid

app = create_app()
app.testing = True

with app.app_context():
    db.create_all()
    
    # Create test user with unique email
    email = f'test{uuid.uuid4().hex[:8]}@example.com'
    user = User(email=email, password_hash='dummy', display_name='Test User')
    db.session.add(user)
    db.session.commit()
    
    # Generate token
    token = create_access_token(user.id)
    print(f"✅ Created user: {user.email}")
    print(f"✅ Generated token: {token[:20]}...")
    
    # Test client
    client = app.test_client()
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test create channel
    print("\n📡 Testing POST /api/channels...")
    res = client.post('/api/channels', 
        json={'name': 'test-channel', 'is_private': False},
        headers=headers
    )
    
    print(f"Status: {res.status_code}")
    print(f"Response: {res.get_data(as_text=True)}")
    
    if res.status_code == 201:
        print("✅ Channel created successfully!")
    else:
        print(f"❌ Error creating channel: {res.status_code}")
