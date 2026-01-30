# config.py
import os

class Config:
    # SQLITE-Datenbank-URI
    SQLALCHEMY_DATABASE_URI = 'sqlite:///data.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your-secret-key-change-this-in-production'
    
    # CORS erlaubte Origins - kann über Umgebungsvariable überschrieben werden
    _default_origins = [
        'https://klimaguessr.cns-studios.com',
        'http://localhost:8081',
        'http://127.0.0.1:8081',
        'https://localhost:8081',
        'https://127.0.0.1:8081'
    ]
    
    _env_origins = os.getenv('CORS_ALLOWED_ORIGINS', '')
    if _env_origins:
        CORS_ALLOWED_ORIGINS = [origin.strip() for origin in _env_origins.split(',') if origin.strip()]
    else:
        CORS_ALLOWED_ORIGINS = _default_origins