import os

class Config(object):
    DEBUG = False
    TESTING = False
    SECRET_KEY = 'SECRET_KEY'
    
    DB_HOST = 'gateway01.eu-central-1.prod.aws.tidbcloud.com'
    DB_PORT = 4000  # TiDB uses port 4000 by default
    DB_USER = '3wRsFFScBW2P8Hp.root'
    DB_PASSWORD = 'ZGQHFb4OELDcn7vB'
    DB_NAME = 'Finance'
    
    # connection string format for mysql-connector-python
    SQLALCHEMY_DATABASE_URI = f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class ProductionConfig(Config):
    pass

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
