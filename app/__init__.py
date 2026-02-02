from flask import Flask
from flask_cors import CORS
from . import database

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Configuration and other setup
    app.config.from_object('app.config.Config')

    # Initialize database
    database.init_app(app)

    # Register blueprint
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
