import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'farmacia-rafa-secret-2024')
    
    DATABASE_URL = os.environ.get('DATABASE_URL', '')
    
    if DATABASE_URL:
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg2://', 1)
        elif DATABASE_URL.startswith('postgresql://') and '+' not in DATABASE_URL:
            DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://', 1)
        if '?' not in DATABASE_URL:
            DATABASE_URL += '?sslmode=require'
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///farmacia.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
