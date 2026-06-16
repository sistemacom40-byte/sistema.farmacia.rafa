import os
import ssl

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'farmacia-rafa-secret-2024')
    
    DATABASE_URL = os.environ.get('DATABASE_URL', '')
    
    if DATABASE_URL:
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+pg8000://', 1)
        elif DATABASE_URL.startswith('postgresql://'):
            DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+pg8000://', 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///farmacia.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    if DATABASE_URL:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        SQLALCHEMY_ENGINE_OPTIONS = {
            'connect_args': {'ssl_context': ssl_context}
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {}
