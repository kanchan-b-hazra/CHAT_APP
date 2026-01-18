from models import db,datetime


# user table
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    oauth_provider = db.Column(db.String(50), nullable=False,default='google')
    oauth_id = db.Column(db.String(255), nullable=False)        # Google sub
    email = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("oauth_provider", "oauth_id", name="uq_oauth_user"),
    )


# conversations
class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)

    type = db.Column(db.String(20), nullable=False,default='private')  # 'private' | 'group'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    participants = db.relationship("ConversationParticipant",back_populates="conversation",cascade="all, delete-orphan")
    messages = db.relationship("Message",back_populates="conversation",cascade="all, delete-orphan",order_by="Message.created_at")


# participents
class ConversationParticipant(db.Model):
    __tablename__ = "conversation_participants"

    id = db.Column(db.Integer, primary_key=True)

    conversation_id = db.Column(db.Integer,db.ForeignKey("conversations.id", ondelete="CASCADE"),nullable=False)

    user_id = db.Column(db.Integer,db.ForeignKey("users.id", ondelete="CASCADE"),nullable=False)

    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    conversation = db.relationship("Conversation", back_populates="participants")
    user = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint("conversation_id", "user_id", name="uq_participant"),
    )


# messages
class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)

    conversation_id = db.Column(db.Integer,db.ForeignKey("conversations.id", ondelete="CASCADE"),nullable=False)

    sender_id = db.Column(db.Integer,db.ForeignKey("users.id", ondelete="CASCADE"),nullable=False)

    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="sent")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    conversation = db.relationship("Conversation", back_populates="messages")
    sender = db.relationship("User")


# online status
class UserPresence(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    last_seen = db.Column(db.DateTime, nullable=False)
    is_online = db.Column(db.Boolean, default=False)
