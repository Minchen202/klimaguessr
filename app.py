import os
from dotenv import load_dotenv
import flask
from flask import request, jsonify, render_template, send_from_directory
from flask_socketio import SocketIO, emit, join_room
import random
import uuid
import string
from werkzeug.security import generate_password_hash, check_password_hash
import threading
import math
from database import db
from config import Config
import db_models
from datetime import datetime
import json
import logging

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

logger.info("Starting application...")

app = flask.Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('secretkey')
app.config.from_object(Config)

db.init_app(app)

print(os.getenv('SECRET_KEY'))

with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Critical error during database initialization: {e}")

socketio = SocketIO(app)

active_lobbies = {}
active_solo_games = {}

try:
    with open('climate_data.json', 'r') as f:
        climateData = json.load(f)
    logger.info(f"Loaded {len(climateData)} climate data points.")
except FileNotFoundError:
    logger.error("climate_data.json not found! Application will fail to start rounds.")
    climateData = []

lobbies_lock = threading.Lock()

def generate_unique_lobby_code(length=6):
    """Generates a unique alphanumeric lobby code."""
    characters = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choice(characters) for i in range(length))
        with lobbies_lock:
            if code not in active_lobbies:
                return code

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat / 2) * math.sin(dLat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dLon / 2) * math.sin(dLon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def broadcast_lobby_update(lobby_code):
    if lobby_code in active_lobbies:
        socketio.emit('lobby_update', {
            'lobby_code': lobby_code,
            'details': active_lobbies[lobby_code]
        }, room=lobby_code)

@socketio.on('start_solo_game')
def handle_start_solo_game():
    socket_id = request.sid
    if not climateData:
        logger.error(f"Solo game failed for {socket_id}: No climate data available.")
        return
    
    active_solo_games[socket_id] = {
        'current_round': 1,
        'score': 0,
        'climate': random.choice(climateData)
    }
    logger.info(f"Solo game started for session: {socket_id}")
    emit('solo_game_start_response', {'success': True, 'message': 'Solo game started!', 'climate': active_solo_games[socket_id]['climate']})

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")
@app.route("/profile.png", methods=["GET"])
def profile_image():
    return send_from_directory('pictures', 'profile.png')

@app.route("/multiplayerhost", methods=["GET"])
def multiplayerhost():
    return render_template("multiplayerhost.html")

@app.route("/multiplayer", methods=["GET"])
def multiplayer():
    return render_template("multiplayer.html")

@app.route("/singleplayer", methods=["GET"])
def singleplayer():
    return render_template("singleplayer.html")

@app.route("/singleplayerlegacy", methods=["GET"])
def singleplayerlegacy():
    return render_template("singleplayerlegacy.html")
  
@app.route("/settings.png", methods=["GET"])
def settings_image():
    return send_from_directory('pictures', 'settings.png')

@app.route('/leaderboard.svg', methods=['GET'])
def leaderboard_icon():
    return send_from_directory('pictures', 'leaderboard.svg')

@socketio.on('submit_solo_guess')
def handle_submit_solo_guess(data):
    socket_id = request.sid
    if socket_id not in active_solo_games:
        logger.warning(f"Guess submitted for non-existent solo session: {socket_id}")
        return

    guess_lat = data.get('guessLat')
    guess_lng = data.get('guessLng')
    game_data = active_solo_games[socket_id]
    climate = game_data['climate']
    
    actual_lat = climate['lat']
    actual_lng = climate['lng']

    dist = calculate_distance(guess_lat, guess_lng, actual_lat, actual_lng)
    points = max(0, round(5000 - dist))
    
    game_data['score'] += points
    logger.info(f"Solo guess received from {socket_id}. Points earned: {points}. Total: {game_data['score']}")
    
    emit('solo_guess_response', {
        'success': True,
        'current_round': game_data['current_round'],
        'name': climate['name'],
        'score': game_data['score'],
        'actual_location': {'lat': actual_lat, 'lng': actual_lng},
        'points_earned': points
    })

@socketio.on('login')
def handle_login(data):
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        logger.warning("Login attempt with missing credentials.")
        emit('login_response', {'success': False, 'message': 'Credentials required.'})
        return

    user = db_models.Users.query.filter_by(username=username).first()

    if user and check_password_hash(user.password, password):
        token = str(uuid.uuid4())
        user.token = token
        db.session.commit()
        logger.info(f"User login successful: {username}")
        emit('login_response', {'success': True, 'token': token, 'username': username})
    else:
        logger.warning(f"Failed login attempt for username: {username}")
        emit('login_response', {'success': False, 'message': 'Invalid credentials.'})

@socketio.on('create_lobby')
def handle_create_lobby():
    try:
        new_lobby_code = generate_unique_lobby_code()
        with lobbies_lock:
            active_lobbies[new_lobby_code] = {
                'status': 'waiting',
                'players': {},
                'active_climate': None,
                'round': 0
            }
        
        join_room(new_lobby_code)
        logger.info(f"Lobby created: {new_lobby_code} by session {request.sid}")
        emit('lobby_created', {'success': True, 'lobby_code': new_lobby_code})
    except Exception as e:
        logger.error(f"Failed to create lobby: {e}")
        emit('lobby_created', {'success': False, 'message': 'Internal server error.'})

@socketio.on('join_lobby')
def handle_join_lobby(data):
    lobby_code = data.get('lobby_code', '').upper()
    nickname = data.get('nickname', '').strip()

    with lobbies_lock:
        if lobby_code not in active_lobbies:
            logger.warning(f"Join attempt for non-existent lobby: {lobby_code}")
            emit('join_result', {'success': False, 'message': 'Lobby not found.'})
            return

        lobby = active_lobbies[lobby_code]
        if nickname in lobby['players']:
            logger.warning(f"Nickname collision in lobby {lobby_code}: {nickname}")
            emit('join_result', {'success': False, 'message': 'Nickname taken.'})
            return

        lobby['players'][nickname] = {
            'nickname': nickname,
            'session_id': request.sid,
            'alreadyguessed': False,
            'guess': None,
            'score': 0
        }

    join_room(lobby_code)
    logger.info(f"Player {nickname} joined lobby {lobby_code}")
    emit('join_result', {'success': True, 'nickname': nickname, 'lobby_code': lobby_code})
    broadcast_lobby_update(lobby_code)

@socketio.on('start_lobby')
def handle_start_lobby(data):
    lobby_code = data.get('lobby_code', '').upper()
    
    if lobby_code not in active_lobbies:
        logger.warning(f"Attempt to start non-existent lobby: {lobby_code}")
        return

    active_lobbies[lobby_code]['status'] = 'playing'
    active_lobbies[lobby_code]['active_climate'] = random.choice(climateData)
    active_lobbies[lobby_code]['round'] = 1

    logger.info(f"Game started in lobby {lobby_code}. Target: {active_lobbies[lobby_code]['active_climate']['name']}")
    socketio.emit('game_started', {
        'success': True,
        'clima': active_lobbies[lobby_code]['active_climate'],
        'round': 1
    }, room=lobby_code)

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client {request.sid} disconnected.")

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 8081))
        logger.info(f"Server is going live on port {port}")
        if os.getenv('DEBUG') == 'True':
            logger.info("Debug mode is ON")
            socketio.run(app, port=port, debug=True)
        else:
            socketio.run(app, port=port)
    except Exception as e:
        logger.error(f"Server crashed: {e}")