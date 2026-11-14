import os
from flask import Flask
from flask_login import LoginManager
from models import db, User

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

    #setup Flask-Login session manager
    login_manager = LoginManager()
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    #register app blueprints
    from routes import main_bp
    app.register_blueprint(main_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)