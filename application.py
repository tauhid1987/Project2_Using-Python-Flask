import os
import urllib.request
from flask import Flask, render_template, request, jsonify, session, redirect
from flask_session import Session
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit
import json

ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
socketio = SocketIO(app)

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Remember all users and channels created
usernames = []
#channels=['general']
channels=['general', 'sports', 'music', 'fashion', 'books']


# A dict with channel and list of all messages details of that channel
channel_msgs = {'general':[],'sports':[],'music':[],'fashion':[],'books':[]}


@app.route("/")
def index():
    username = session.get('username')
    if not username:
        return render_template('login.html')
    else:
        return render_template('index.html', username=username,channels=channels, channel_msgs=channel_msgs)


@app.route("/login", methods = ["POST"])
def login():
    username = request.form.get('display-name')
    # Store the username in session
    session['username'] = username
    usernames.append(username)
    #return redirect('/')
    return render_template('index.html', username=username,channels=channels, channel_msgs=channel_msgs)


@socketio.on("new msg")
def messages(data):
    username = data["username"]
    msg = data["msg"]
    channel = data["channel"]
    dateTime = data["dateTime"]

    if len(channel_msgs[channel]) >= 100:
        emit("announce message", {"success": False})
    else:
        channel_msgs[channel].append([username, dateTime, msg])
        emit("announce message", {"success": True, "channel": channel, "username": username,"dateTime": dateTime, "msg": msg}, broadcast=True)


@socketio.on("new channel")
def new_channel(data):
    channel = data["channel"]
    username = data["username"]

    if channel in channels:
        emit("announce channel", {"success": False})
    else:
        channels.append(channel)
        channel_msgs[channel] = []
        emit("announce channel", {"success":True, "channel": channel, "username":username}, broadcast=True)


@app.route('/channel/<channel>')
def channel(channel):
    """When user changes a channel."""
    return json.dumps(channel_msgs[channel])


@app.route('/delete_msg/<activeChannel>/<hiddenMsg>')
def delete_msg(activeChannel, hiddenMsg):
    msg = list(hiddenMsg.split(","))
    msg.pop()
    msgs_list = channel_msgs[activeChannel]
    for i in range(len(msgs_list)):
        if msgs_list[i] == msg:
            del channel_msgs[activeChannel][i]
            return 'OK'
    
    return 'OK'
    

# Private Chat for Users
users = {}

@app.route('/private')
def private():
    return render_template('private.html')

@app.route('/orginate')
def orginate():
    socketio.emit('server orginated', 'Something happened on the server!')
    return '<h1>Sent!</h1>'

@socketio.on('message from user', namespace='/messages')
def receive_message_from_user(message):
    print('USER MESSAGE: {}'.format(message))
    emit('from flask', message.upper(), broadcast=True)

@socketio.on('username', namespace='/private')
def receive_username(username):
    users[username] = request.sid
    #users.append({username : request.sid})
    #print(users)
    print('Username added!')

@socketio.on('private_message', namespace='/private')
def private_message(payload):
    recipient_session_id = users[payload['username']]
    message = payload['message']

    emit('new_private_message', message, room=recipient_session_id)




if __name__ == '__main__':
    socketio.run(app, debug=True)   
