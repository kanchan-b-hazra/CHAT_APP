from models.model import ConversationParticipant,User


def get_other_user_ids(conversation_id, current_user_id):
    participants = (
        ConversationParticipant.query
        .filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id != current_user_id
        )
        .first()
    )
    user=User.query.filter_by(id=participants.user_id).first()
    return user