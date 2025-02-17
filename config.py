import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    POSTS_PER_PAGE = 10
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    UPLOAD_FOLDER = r'B:\microblog\tmp'