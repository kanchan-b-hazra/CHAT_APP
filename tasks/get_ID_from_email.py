from models.model import User
from models import db

def get_idFrom_Email(email):
    user=User.query.filter_by(email=email).first()
    if user:
        return user.id
    else:
        return -1