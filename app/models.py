from . import db
from datetime import datetime
import uuid


def gen_uuid():
    return str(uuid.uuid4())


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {"id": self.id, "email": self.email, "display_name": self.display_name}


class Channel(db.Model):
    __tablename__ = 'channels'
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    name = db.Column(db.String(255), nullable=False)
    is_private = db.Column(db.Boolean, default=False)
    owner_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        member_count = ChannelMembership.query.filter_by(channel_id=self.id).count()
        return {"id": self.id, "name": self.name, "is_private": self.is_private, "owner_id": self.owner_id, "member_count": member_count}


class ChannelMembership(db.Model):
    __tablename__ = 'channel_memberships'
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    channel_id = db.Column(db.String(36), db.ForeignKey('channels.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.String(50), default='member')
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    channel_id = db.Column(db.String(36), db.ForeignKey('channels.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    edited_at = db.Column(db.DateTime, nullable=True)
    is_deleted = db.Column(db.Boolean, default=False)

    def to_dict(self, user=None):
        user_obj = None
        if user:
            user_obj = {'id': user.id, 'display_name': user.display_name}
        elif self.user_id:
            # Lazy load user if not provided
            from . import db as database
            user = database.session.query(User).get(self.user_id)
            if user:
                user_obj = {'id': user.id, 'display_name': user.display_name}
        
        return {
            'id': self.id,
            'channel_id': self.channel_id,
            'user_id': self.user_id,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'edited_at': self.edited_at.isoformat() if self.edited_at else None,
            'is_deleted': self.is_deleted,
            'user': user_obj or {'id': self.user_id, 'display_name': 'Unknown'}
        }


class RefreshToken(db.Model):
    __tablename__ = 'refresh_tokens'
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
