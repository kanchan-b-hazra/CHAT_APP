from models.model import UserPresence
from datetime import datetime

def is_user_online(user_id):
    p = UserPresence.query.get(user_id)
    if not p:
        return False
    return (datetime.utcnow() - p.last_seen).seconds < 30
