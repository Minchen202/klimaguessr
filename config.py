# config.py
import os

class Config:
    # SQLITE-Datenbank-URI
    SQLALCHEMY_DATABASE_URI = 'sqlite:///data.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your-secret-key-change-this-in-production'
    
    # CORS allowed origins - can be overridden via environment variable
    CORS_ALLOWED_ORIGINS = os.getenv(
        'CORS_ALLOWED_ORIGINS',
        'https://klimaguessr.cns-studios.com,http://localhost:8081,http://127.0.0.1:8081,https://localhost:8081,https://127.0.0.1:8081'
    ).split(',')