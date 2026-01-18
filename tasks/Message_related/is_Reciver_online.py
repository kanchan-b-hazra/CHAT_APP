from models.model import ConversationParticipant
from tasks.Message_related.hartbit_update import is_user_online

def is_reciver_online(conv_id,user_id):
    participate_info = (
        ConversationParticipant.query
        .filter(
            ConversationParticipant.conversation_id == conv_id,
            ConversationParticipant.user_id != user_id
        )
        .first()
    )
    receiver_online = is_user_online(participate_info.user_id)
    return receiver_online