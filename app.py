import time
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

app = flask.Flask(__name__)
app.config['SECRET_KEY'] = 'd711deff-6edd-4364-933b-62d7702806cc'

app.config.from_object(Config)

db.init_app(app)

with app.app_context():
    db.create_all()

socketio = SocketIO(app, cors_allowed_origins="*")

active_lobbies = {}
active_solo_games = {}



# Load climate data from JSON file
with open('climate_data.json', 'r') as f:
  climateData = json.load(f)

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
    distance = R * c
    return distance

def broadcast_lobby_update(lobby_code):
    if lobby_code in active_lobbies:
        socketio.emit('lobby_update', {
            'lobby_code': lobby_code,
            'details': active_lobbies[lobby_code]
        },room=lobby_code)

@socketio.on('start_solo_game')
def handle_start_solo_game():
    socket_id = request.sid
    active_solo_games[socket_id] = {
        'current_round': 1,
        'score': 0,
        'climate': random.choice(climateData)
    }
    emit('solo_game_start_response', {'success': True, 'message': 'Solo game started!', 'climate': active_solo_games[socket_id]['climate']})

@socketio.on('resize_chart')
def handle_resize_chart(data):
    socket_id = request.sid
    if socket_id not in active_solo_games:
        emit('solo_guess_response', {'success': False, 'message': 'No active solo game found.'})
        return
    emit('resize_chart_response', {
        'climate': active_solo_games[socket_id]['climate'],
        'big': data.get('big')
    })

@socketio.on('submit_solo_guess')
def handle_submit_solo_guess(data):
    socket_id = request.sid
    guess_lat = data.get('guessLat')
    guess_lng = data.get('guessLng')

    game_data = active_solo_games[socket_id]
    climate = game_data['climate']
    actual_lat = climate['lat']
    actual_lng = climate['lng']

    lat_distance = abs((guess_lat - actual_lat)) * 111  # approx km per degree latitude
    lon_distance = abs((guess_lng - actual_lng)) * 111  # approx km per degree longitude

    lat_points = 0 if lat_distance > 2500 else round(2500 - lat_distance)
    lon_points = 0 if lon_distance > 2500 else round(2500 - lon_distance)
    points = lat_points + lon_points

    game_data['score'] += points
    emit('solo_guess_response', {
        'success': True,
        'message': f'Round {game_data["current_round"]} started!',
        'current_round': game_data['current_round'],
        "name": climate['name'],
        'score': game_data['score'],
        'actual_location': {'lat': actual_lat, 'lng': actual_lng},
        "total_points": game_data['score'],
        'points_earned': points
    })

@socketio.on("start_solo_round")
def handle_solo_start_round():
    socket_id = request.sid
    if socket_id not in active_solo_games:
        emit('solo_guess_response', {'success': False, 'message': 'No active solo game found.'})
        return
    active_solo_games[socket_id]['current_round'] += 1
    active_solo_games[socket_id]['climate'] = random.choice(climateData)
    emit('solo_round_started', {
        'success': True,
        'message': f'Round {active_solo_games[socket_id]["current_round"]} started!',
        'climate': active_solo_games[socket_id]['climate'],
        "current_round": active_solo_games[socket_id]['current_round'],
        "total_score": active_solo_games[socket_id]['score']
    })

@socketio.on("delete_solo_game")
def handle_delete_solo_game():
    socket_id = request.sid
    if socket_id in active_solo_games:
        del active_solo_games[socket_id]
        emit('solo_game_deleted', {'success': True, 'message': 'Solo game deleted successfully.'})
    else:
        emit('solo_game_deleted', {'success': False, 'message': 'No active solo game found.'})

@socketio.on("save_solo_game")
def handle_save_solo_game(data):
    socket_id = request.sid
    token = data.get('token')
    username = db_models.Users.query.filter_by(token=token).first()
    print(db_models.Users.query.filter_by(username=username).first())
    if socket_id not in active_solo_games:
        emit('save_solo_response', {'success': False, 'message': 'No active solo game found.'})
        return
    if not username or username not in str(db_models.Users.query.filter_by(username=username).first()).split(";")[0]:
        emit('save_solo_response', {'success': False, 'message': 'Invalid username.'})
        return

    game_data = db_models.Leaderboard(username=username, score=active_solo_games[socket_id]['score'], timestamp=datetime.now())
    db.session.add(game_data)
    db.session.commit()
    print(f'Solo game saved for user: {username} with score: {active_solo_games[socket_id]["score"]}')
    emit('save_solo_response', {'success': True, 'message': 'Solo game saved successfully!'})



@socketio.on('get_leaderboard')
def handle_get_leaderboard():
    # Alle Einträge abfragen, absteigend nach score sortieren
    leaderboard_data = db_models.Leaderboard.query.order_by(db_models.Leaderboard.score.desc()).all()

    # Die Daten für den Client formatieren
    leaderboard = [{
        'username': entry.username,
        'score': entry.score,
        'timestamp': entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for entry in leaderboard_data]

    # Daten an den Client senden
    socketio.emit('leaderboard_update', leaderboard)

@socketio.on('register')
def handle_register(data):
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if not username or not password:
        emit('registration_response', {'success': False, 'message': 'Username and password are required.'})
        return

    if db_models.Users.query.filter_by(username=username).first():
      emit('registration_response', {'success': False, 'message': 'Username already exists.'})
      return

    hashed_password = generate_password_hash(password)

    new_user = db_models.Users(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    print(f'New user registered: {username}')
    emit('registration_response', {'success': True, 'message': 'Registration successful!'})

@socketio.on('login')
def handle_login(data):
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        emit('login_response', {'success': False, 'message': 'Username and password are required.'})
        return

    user_data_raw = db_models.Users.query.filter_by(username=username).first()

    user_data = [str(user_data_raw).split(";")[0], str(user_data_raw).split(";")[1]]

    if not user_data:
        emit('login_response', {'success': False, 'message': 'Invalid username or password.'})
        return

    if check_password_hash(user_data[1], password):
        token = str(uuid.uuid4())
        
        db_models.Users.query.filter_by(username=username).update({'token': token})
        db.session.commit()

        print(f'User logged in: {username} with token: {token}')
        emit('login_response', {'success': True, 'message': 'Login successful!', 'token': token, 'username': username})
    else:
        emit('login_response', {'success': False, 'message': 'Invalid username or password.'})

@socketio.on('authenticate')
def handle_authenticate(data):
    
    token = data.get('token')
    
    username = str(db_models.Users.query.filter_by(token=token).first()).split(";")[0]

    if username:
        emit('auth_response', {
            'success': True,
            'message': f'Welcome, {username}! Your token is valid.',
            'username': username
        })
    else:
        emit('auth_response', {'success': False, 'message': 'Authentication failed. Invalid or expired token.'})

@app.route("/is_lobby_joinable", methods=["POST"])
def is_lobby_joinable():
    data = request.get_json()
    lobby_code = data["lobby_code"]
    with lobbies_lock:
        if lobby_code in active_lobbies and active_lobbies[lobby_code]["status"] == "waiting":
            return jsonify({
                "joinable": True
            })
        else:
            return jsonify({
                "joinable": False
            })
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

@app.route("/legal", methods=["GET"])
def legal():
    return render_template("legal.html")

@app.route("/singleplayerlegacy", methods=["GET"])
def singleplayerlegacy():
    return render_template("singleplayerlegacy.html")
  
@app.route("/settings.png", methods=["GET"])
def settings_image():
    return send_from_directory('pictures', 'settings.png')
@socketio.on('connect')
def handle_connect():
    print(f'Client {request.sid} connected')
    emit('connected', {'message': 'Successfully connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client {request.sid} disconnected')
  

@socketio.on('create_lobby')
def handle_create_lobby():
    try:

        new_lobby_code = generate_unique_lobby_code()

        with lobbies_lock:
            active_lobbies[new_lobby_code] = {
                'status': 'waiting',
                'players': {},
                'active_climate': None,
                'round': None
            }
        
        # Join the Socket.IO room for this lobby
        join_room(new_lobby_code)
        print(f"Lobby created: {new_lobby_code}. Total active lobbies: {len(active_lobbies)}")

        emit('lobby_created', {
            'success': True,
            'lobby_code': new_lobby_code,
            'message': 'Lobby created successfully. Share this code with your friends!'
        })

    except Exception as e:
        print(f"Error creating lobby: {e}")
        emit('lobby_created', {
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })
@socketio.on("register_player")
def reg(data):
    nickname = data.get('nickname', None)
    lobby_code = data.get('lobby_code', None)
    if not lobby_code or not nickname:
        emit('register_result', {
            'error_code': 'missing_fields',
            'success': False,
            'message': "Lobby code and nickname are required."
        })
        return

    if len(nickname) > 10:
        emit('register_result', {
            'success': False,
            'message': "Nickname is too long."
        })
        return

    with lobbies_lock:
        if lobby_code not in active_lobbies:
            emit('register_result', {
                'success': False,
                'error_code': 'lobby_not_found',
                'message': f"Lobby '{lobby_code}' not found."
            })
            return
        if not nickname in active_lobbies[lobby_code]['players'] and not nickname == "Host":
            emit('register_result', {
                'success': False,
                'message': "Nickname doesn't exist in the lobby.",
                'error_code': 'nickname_not_found'
            })
            return
        
    join_room(lobby_code)

    emit('register_result', {
        'success': True,
        'message': "Successfully registered."
    })

@socketio.on('join_lobby')
def handle_join_lobby(data):
    try:
        lobby_code = data['lobby_code'].upper()
        nickname = data['nickname']

        if not lobby_code or not nickname:
            emit('join_result', {
                'success': False,
                'message': "Lobby code and nickname are required."
            })
            return
        if nickname == "":
            emit('join_result', {
                'success': False,
                'message': "Nickname cannot be empty."
            })
            return

        with lobbies_lock:
            if lobby_code not in active_lobbies:
                emit('join_result', {
                    'success': False,
                    'message': f"Lobby '{lobby_code}' not found."
                })
                return

            if len(active_lobbies[lobby_code]['players']) >= 8:
                emit('join_result', {
                    'success': False,
                    'message': "Lobby is full."
                })
                return

            if len(nickname) >= 10:
                emit('join_result', {
                    'success': False,
                    'message': "Nickname is too long."
                })
                return

            if nickname in active_lobbies[lobby_code]['players']:
                emit('join_result', {
                    'success': False,
                    'message': "Nickname already taken."
                })
                return

            # Add player to lobby
            active_lobbies[lobby_code]['players'][nickname] = {
                'nickname': nickname,
                'session_id': request.sid,
                'alreadyguessed': False,
                'guess': None,
                'score': 0
            }

        # Join the Socket.IO room for this lobby
        join_room(lobby_code)
        print(f"Player '{nickname}' joined lobby '{lobby_code}'")
        emit('join_result', {
            'success': True,
            "nickname": nickname,
            'message': f"Successfully joined lobby '{lobby_code}' as {nickname}",
            'lobby_code': lobby_code
        })

        # Broadcast to all players in the lobby that someone joined
        broadcast_lobby_update(lobby_code)

    except Exception as e:
        print(f"Error joining lobby: {e}")
        emit('join_result', {
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

@socketio.on('start_lobby')
def handle_start_lobby(data):
    """Handle starting a lobby game"""
    try:
        lobby_code = data['lobby_code'].upper()

        if lobby_code not in active_lobbies:
            emit('start_result', {
                'success': False,
                'message': f"Lobby '{lobby_code}' not found."
            })
            return

        active_lobbies[lobby_code]['status'] = 'playing'
        active_lobbies[lobby_code]['active_climate'] = random.choice(climateData)
        active_lobbies[lobby_code]['round'] = 1

        print(f"Lobby '{lobby_code}' started with climate {active_lobbies[lobby_code]['active_climate']}")

        # Broadcast to all players in the lobby that the game started
        socketio.emit('game_started', {
            'success': True,
            'message': f"Game started in lobby '{lobby_code}'",
            'clima': active_lobbies[lobby_code]['active_climate'],
            'round': active_lobbies[lobby_code]['round']
        }, room=lobby_code)

    except Exception as e:
        print(f"Error starting lobby: {e}")
        emit('start_result', {
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

@socketio.on('make_guess')
def handle_guess(data):
    try:
        lobby_code = data['lobby_code'].upper()
        nickname = data['nickname']
        guess = data['guess']

        if lobby_code not in active_lobbies or active_lobbies[lobby_code]['status'] != 'playing':
            emit('guess_result', {
                'success': False,
                'message': f"Lobby '{lobby_code}' not found or not started yet."
            })
            return

        if nickname not in active_lobbies[lobby_code]['players']:
            emit('guess_result', {
                'success': False,
                'message': f"Player '{nickname}' not found in lobby '{lobby_code}'."
            })
            return

        if active_lobbies[lobby_code]['players'][nickname]['alreadyguessed']:
            emit('guess_result', {
                'success': False,
                'message': f"Player '{nickname}' has already guessed."
            })
            return

        # Record the guess
        active_lobbies[lobby_code]['players'][nickname]['alreadyguessed'] = True
        active_lobbies[lobby_code]['players'][nickname]['guess'] = guess

        emit('guess_result', {
            'success': True,
            'message': 'Guess submitted successfully.',
            'guess': guess
        })

        print(f"Player '{nickname}' made a guess: {guess}")

        already_guessed = [p['nickname'] for p in active_lobbies[lobby_code]['players'].values() if p['alreadyguessed']]
        not_guessed = [p['nickname'] for p in active_lobbies[lobby_code]['players'].values() if not p['alreadyguessed']]

        # Broadcast to all players that someone made a guess
        socketio.emit('player_guessed', {
            'already_guessed': already_guessed,
            'not_guessed': not_guessed,
        }, room=lobby_code)

    except Exception as e:
        print(f"Error handling guess: {e}")
        emit('guess_result', {
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

@socketio.on('end_round')
def handle_end_round(data):
    """Handle ending a round and calculating scores"""
    try:
        lobby_code = data['lobby_code'].upper()

        if lobby_code not in active_lobbies or active_lobbies[lobby_code]['status'] != 'playing':
            emit('end_result', {
                'success': False,
                'message': f"Lobby '{lobby_code}' not found or not in playing state."
            })
            return

        active_lobbies[lobby_code]['status'] = 'result'

        # Calculate scores for all players
        for player in active_lobbies[lobby_code]['players']:
            if not active_lobbies[lobby_code]['players'][player]['alreadyguessed']:
                continue

            distance = calculate_distance(
                active_lobbies[lobby_code]['active_climate']['lat'],
                active_lobbies[lobby_code]['active_climate']['lng'],
                active_lobbies[lobby_code]['players'][player]['guess']['lat'],
                active_lobbies[lobby_code]['players'][player]['guess']['lng']
            )

            if distance > 5000:
                points = 0
            else:
                points = round(5000 - distance)
            if distance < 300:
                points = 5000
            elif distance < 1500:
                points = round(4000 + (500 - distance) * 2)
            elif distance < 3000:
                points = round(3000 + (1000 - distance))

            active_lobbies[lobby_code]['players'][player]['score'] += points

        # Broadcast results to all players
        socketio.emit('round_ended', {
            'success': True,
            'message': f"Round ended in lobby '{lobby_code}'",
            'details': active_lobbies[lobby_code],
            'actual_location_lat': active_lobbies[lobby_code]['active_climate']['lat'],
            'actual_location_lng': active_lobbies[lobby_code]['active_climate']['lng']
        }, room=lobby_code)

    except Exception as e:
        print(f"Error ending round: {e}")
        emit('end_result', {
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

@socketio.on('start_new_round')
def handle_start_new_round(data):
    try:
        lobby_code = data['lobby_code'].upper()

        if lobby_code not in active_lobbies or active_lobbies[lobby_code]['status'] != 'result':
            emit('new_round_result', {
                'success': False,
                'message': f"Lobby '{lobby_code}' not found or not in result state."
            })
            return

        active_lobbies[lobby_code]['status'] = 'playing'
        active_lobbies[lobby_code]['active_climate'] = random.choice(climateData)
        active_lobbies[lobby_code]['round'] += 1

        # Reset player guesses
        for nickname in active_lobbies[lobby_code]['players']:
            active_lobbies[lobby_code]['players'][nickname]['alreadyguessed'] = False
            active_lobbies[lobby_code]['players'][nickname]['guess'] = None

        # Broadcast new round to all players
        socketio.emit('new_round_started', {
            'success': True,
            'all_players': list(active_lobbies[lobby_code]['players'].keys()),
            'message': 'New round started!',
            'active_climate': active_lobbies[lobby_code]['active_climate'],
            'round': active_lobbies[lobby_code]['round']
        }, room=lobby_code)

    except Exception as e:
        print(f"Error starting new round: {e}")
        emit('new_round_result', {
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })
@socketio.on('end_game')
def handle_end_game(data):
    try:
        lobby_code = data['lobby_code'].upper()

        if lobby_code not in active_lobbies or active_lobbies[lobby_code]['status'] != 'result':
            emit('end_game_result', {
                'success': False,
                'message': f"Lobby '{lobby_code}' not found or not in result state."
            })
            return

        # Reset the lobby
        with lobbies_lock:
            del active_lobbies[lobby_code]

        print(f"Game ended and lobby '{lobby_code}' deleted.")

        emit('end_game', {
            'lobby_code': lobby_code,
            'message': f"Game ended and lobby '{lobby_code}' deleted."
        }, room=lobby_code)

        emit('end_game_result', {
            'success': True,
            'message': f"Game ended and lobby '{lobby_code}' deleted."
        })

    except Exception as e:
        print(f"Error ending game: {e}")
        emit('end_game_result', {
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })
@socketio.on('get_lobby_info')
def handle_get_lobby_info(data):
    if not data:
        emit('lobby_info', {
            'success': False,
            'message': "No data provided."
        })
        return
    if 'lobby_code' not in data:
        emit('lobby_info', {
            'success': False,
            'message': "Lobby code is required."
        })
        return
    try:
        lobby_code = data['lobby_code'].upper()

        with lobbies_lock:
            lobby = active_lobbies.get(lobby_code)

        if lobby:
            emit('lobby_info', {
                'success': True,
                'lobby_code': lobby_code,
                'details': lobby,
                'all_players': list(lobby['players'].keys())
            })
        else:
            emit('lobby_info', {
                'success': False,
                'message': f"Lobby '{lobby_code}' not found."
            })

    except Exception as e:
        print(f"Error getting lobby info: {e}")
        emit('lobby_info', {
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

if __name__ == '__main__':
    socketio.run(app,debug=True, port=8081)
