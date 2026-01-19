from flask import Flask,request,session,redirect,jsonify
from flask_cors import CORS
from flask_socketio import SocketIO,emit,send,join_room,leave_room,disconnect
from tasks.is_conversation_exist import get_common_conversation
from models import db
from authlib.integrations.requests_client import OAuth2Session
from flask_jwt_extended import JWTManager,create_access_token,create_refresh_token,jwt_required,get_jwt_identity
from datetime import datetime,timedelta
from models.model import ConversationParticipant, User,Conversation,Message,UserPresence
from tasks.get_ID_from_email import get_idFrom_Email
from tasks.get_other_user import get_other_user_ids
from tasks.Message_related.message_obj import to_dict
from tasks.Message_related.is_Reciver_online import is_reciver_online
import os
from urllib.parse import quote_plus


app=Flask(__name__)
app.secret_key=os.getenv("SECRET_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CA_PATH = quote_plus(os.path.join(BASE_DIR, "ca.pem"))

# db setup
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://3GxrazQgsPKSzm3.root:ZglNci5Ba6XzJwxy"
    f"@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/test"
    f"?ssl_ca={CA_PATH}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ---------- GOOGLE CONFIG ----------
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
REDIRECT_URI =os.getenv('REDIRECT_URI')
SCOPE = "openid email profile"
FRONTEND_URL =os.getenv('FRONTEND_URL')

# ---------- JWT CONFIG ----------
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)


jwt=JWTManager(app)
socketio=SocketIO(app,cors_allowed_origins='*',async_mode='threading')

db.init_app(app)
CORS(app,supports_credentials=True)








# Routes
@app.route('/')
def home():
    return 'From flask home rought.'


# LOGIN
@app.route("/oauth/google")
def google_login():
    google = OAuth2Session(
        client_id=GOOGLE_CLIENT_ID,
        scope=SCOPE,
        redirect_uri=REDIRECT_URI
    )
    authorization_url, state = google.create_authorization_url(AUTHORIZE_URL)
    session["oauth_state"] = state  # CSRF protection
    return redirect(authorization_url)


@app.route("/oauth/google/callback")
def google_callback():
    # Google sends ?code=XXX
    code = request.args.get("code")
    if not code:
        return jsonify({'msg':"Missing code. Did you open this URL manually?",'state':0}), 400

    google = OAuth2Session(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        state=session.get("oauth_state")
    )

    token = google.fetch_token(
        TOKEN_URL,
        authorization_response=request.url,
        grant_type='authorization_code'
    )

    resp = google.get(USERINFO_URL)
    user_info = resp.json()
    # return user_info
    user=User.query.filter_by(oauth_id=user_info["id"]).first()
    if user:
        access_token=create_access_token(identity=str(user.id))
        refresh_token=create_refresh_token(identity=str(user.id))
        # return jsonify({
        #     "status": "logged_in",
        #     "access_token": access_token,
        #     "refresh_token": refresh_token,
        #     'state':1
        # })
        response = redirect(
            f"{FRONTEND_URL}/oauthsuccess?access_token={access_token}"
        )

        # 🔐 secure refresh token
        response.set_cookie(
            "refresh_token",
            refresh_token,
            httponly=True,
            samesite=None,
            secure=False
        )
        return response
    else:
        new_user=User(
            oauth_id=user_info["id"],
            email=user_info["email"],
            name=user_info["name"],
            avatar_url=user_info["picture"]
        )
        db.session.add(new_user)
        db.session.commit()
        access_token=create_access_token(identity=str(new_user.id))
        refresh_token=create_refresh_token(identity=str(new_user.id))

        # return jsonify({
        #     "status": "logged_in",
        #     "access_token": access_token,
        #     "refresh_token": refresh_token,
        #     'state':1
        # })
        response = redirect(
            f"{FRONTEND_URL}/oauthsuccess?access_token={access_token}"
        )

        # 🔐 secure refresh token
        response.set_cookie(
            "refresh_token",
            refresh_token,
            httponly=True,
            samesite=None,
            secure=False
        )
        return response
    return jsonify({'msg':"Could not fetch your information.",'state':0}), 400


@app.route("/get_token",methods=['POST'])
@jwt_required(refresh=True)
def get_new_token():
    user_id = get_jwt_identity()
    new_access = create_access_token(identity=user_id)
    return jsonify(access_token=new_access)


# add new conversation
@app.route('/add_conversation',methods=['POST'])
@jwt_required()
def add_conversation():
    user_user_id = int(get_jwt_identity())
    data = request.get_json()
    conector_email = data.get('conector_email')
    conector_id=get_idFrom_Email(conector_email)

    if user_user_id==conector_id:
        return jsonify({'msg': 'Cannot create conversation with yourself'}), 400
    if conector_id==-1:
        return jsonify({'msg': 'Connector email does not exist'}), 400

    if not user_user_id or not conector_id:
        return jsonify({'msg': 'Missing user IDs'}), 400

    # Check if conversation already exists
    common_conversation = get_common_conversation(user_user_id, conector_id)
    
    if common_conversation:
        return jsonify({'msg': 'Conversation already exists','status':0}), 400

    # Create new conversation
    new_conversation = Conversation(type="private")
    db.session.add(new_conversation)
    db.session.flush()

    # Add participants
    participant1 = ConversationParticipant(
        conversation_id=new_conversation.id,
        user_id=user_user_id
    )
    participant2 = ConversationParticipant(
        conversation_id=new_conversation.id,
        user_id=conector_id
    )
    db.session.add(participant1)
    db.session.add(participant2)
    db.session.commit()

    return jsonify({
        'msg': 'Conversation created successfully',
        'conversation_id': new_conversation.id,
        'status':1
    }), 200
    # return jsonify({'msg': 'Conversation does not exist','status':1}), 200


# get all chat list
@app.route('/get_chats')
@jwt_required()
def get_chats():
    user_id = int(get_jwt_identity())

    participants = ConversationParticipant.query.filter_by(
        user_id=user_id
    ).all()

    # chat_ids = [p.conversation_id for p in participants]
    chat_infos=[]
    for i in participants:
        relative_obj=get_other_user_ids(i.conversation_id,user_id)
        chat_infos.append({'user_id':user_id,"name":relative_obj.name,"chat_id":i.conversation_id,"image_url":relative_obj.avatar_url})


    return jsonify({
        'status': 1,
        'chat_infos': chat_infos
    }), 200


@app.route('/get_chat_messages/<int:conv_id>')
@jwt_required()
def get_chat_messages(conv_id):
    user_id=int(get_jwt_identity())

    # ✅ check user is part of the conversation
    is_participant = ConversationParticipant.query.filter_by(
        conversation_id=conv_id,
        user_id=user_id
    ).first()

    if not is_participant:
        return jsonify({"msg": "Unauthorized access"}), 403
    
    # ✅ get messages of that conversation
    messages = Message.query.filter_by(
        conversation_id=conv_id
    ).order_by(Message.created_at.asc()).all()

    return jsonify({
        "status": 1,
        "messages": [to_dict(m) for m in messages]
    }), 200


# online hartbit.
@app.route("/heartbeat", methods=["POST"])
@jwt_required()
def heartbeat():
    user_id = int(get_jwt_identity())

    presence = UserPresence.query.get(user_id)
    if not presence:
        presence = UserPresence(user_id=user_id)

    presence.last_seen = datetime.utcnow()
    presence.is_online = True

    db.session.add(presence)
    db.session.commit()

    return jsonify({"status": "online"})









# Events
@socketio.on('connect')
def handle_connect():
    print("🟢 Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    print("🔴 Client disconnected")

@socketio.on('message')
def handel_message(data):
    print(f'Message from cliend side {data['msg']}')
    send({'msg':'Hello from Flask server'})

@socketio.on('join_room')
def handel_join(data):
    room=data['room']
    join_room(room)
    join_room(data['notification_room'])
    print(f'User joined room {room} and {data['notification_room']}')

@socketio.on("leave_room")
def handle_leave(data):
    room = data.get("room")
    leave_room(room)
    leave_room(data['notification_room'])
    print(f"User left room: {room} and {data['notification_room']}")

@socketio.on('room_message')
def handel_room_message(data):
    online_status=is_reciver_online(data['conversation_id'],data['user_id'])
    if online_status:
        message=Message(
            conversation_id=data['conversation_id'],
            sender_id=data['user_id'],
            content=data['msg'],
            status="delivered"
        )
    else:
        message=Message(
            conversation_id=data['conversation_id'],
            sender_id=data['user_id'],
            content=data['msg']
        )
    db.session.add(message)
    db.session.flush()
    # db.session.commit()
    send({'created_at':str(message.created_at),'message':data['msg'],'id':message.id,'sender_id':data['user_id'],"status":message.status},room=data['room'])
    # print(f"ID----------{message.id}")
    db.session.commit()

# when boath user in same room live
@socketio.on("message_delivered")
def message_deliver(data):
    message_id = data.get("message_id")
    msg = Message.query.get(message_id)
    # print(f"---------{msg}")
    if msg and msg.status != "read":
        msg.status = "read"
        db.session.commit()

        emit("message_status", {
            "message_ids": [msg.id],
            "status": "read"
        }, room=f"user_{msg.sender_id}")

@socketio.on("message_read")
def message_read(data):
    msg = Message.query.get(data["message_id"])
    if msg and msg.status != "read":
        msg.status = "read"
        db.session.commit()

        emit("message_status", {
            "message_id": msg.id,
            "status": "read"
        }, room=f"user_{msg.sender_id}")

@socketio.on("join_room_notify")
def room_join_notify(data):
    room=data['room']
    user_id=data['user_id']
    participate_info = (
        ConversationParticipant.query
        .filter(
            ConversationParticipant.conversation_id == data['room'],
            ConversationParticipant.user_id != data['user_id']
        )
        .first()
    )

    # when receiver connects / joins room
    unread_messages = Message.query.filter(
        Message.conversation_id == room,
        Message.sender_id != user_id,
        Message.status != "read"
    ).all()

    # mark all as delivered
    for msg in unread_messages:
        msg.status = "read"
    db.session.commit()

    emit("message_status",{
        "conversation_id": room,
        "message_ids": [m.id for m in unread_messages],
        "status": "read"
    },room=f"user_{participate_info.user_id}")
    # print(f'inform to user_id {participate_info.user_id} to join.')


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True
    )



