#!/usr/bin/env python
"""Initialize default channels in the database."""

from app import create_app, db
from app.models import Channel

def init_channels():
    app = create_app()
    with app.app_context():
        # Check if channels already exist
        if Channel.query.first():
            print("Channels already exist. Skipping initialization.")
            return
        
        # Create default channels
        channels_data = [
            {'name': 'general', 'is_private': False},
            {'name': 'fun', 'is_private': False},
            {'name': 'ai', 'is_private': False},
            {'name': 'technology', 'is_private': False},
            {'name': 'random', 'is_private': False},
        ]
        
        for data in channels_data:
            channel = Channel(**data)
            db.session.add(channel)
        
        db.session.commit()
        print(f"✅ Created {len(channels_data)} default channels")
        for ch in Channel.query.all():
            print(f"  - #{ch.name}")

if __name__ == '__main__':
    init_channels()
