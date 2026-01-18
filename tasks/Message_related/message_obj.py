def to_dict(m):
    return {
        "id": m.id,
        "sender_id": m.sender_id,
        "message": m.content,
        "created_at": m.created_at.isoformat(),
        "status":m.status
    }
