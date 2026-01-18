from sqlalchemy import func
from models.model import ConversationParticipant,Conversation
from models import db

def get_common_conversation(user1_id, user2_id):
    conversations1 = ConversationParticipant.query.filter_by(user_id=user1_id).all()
    conversations2 = ConversationParticipant.query.filter_by(user_id=user2_id).all()
    
    conv_ids_1 = {c.conversation_id for c in conversations1}
    conv_ids_2 = {c.conversation_id for c in conversations2}
    
    common_conv_ids = conv_ids_1 & conv_ids_2
    # print(common_conv_ids)
    if common_conv_ids:
        conversation = Conversation.query.filter(
            Conversation.id.in_(common_conv_ids)
        ).first()
        return conversation
    else:
        return None