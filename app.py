import os
from flask import Flask
from models import db

def create_app():
    app = Flask(__name__)

    #Secret key for sessions
    app.config['SECRET_KEY'] = 'emp-project-secret-key'

    #Store SQLite db in the 'instance' folder
    base_dir = os.path.abspath(os.path.dirname(__file__))
    os.makedirs(os.path.join(base_dir, 'instance'), exist_ok=True)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'instance', 'emp.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)