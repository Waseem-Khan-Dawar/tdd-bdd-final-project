from flask import Flask

# Factory function to create and configure the app
def create_app():
    app = Flask(__name__)

    # Load configuration
    app.config.from_object("service.config.Config")

    # Initialize extensions
    from service.models import db
    db.init_app(app)

    # Register blueprints/routes
    from service.routes import api_blueprint
    app.register_blueprint(api_blueprint)

    return app
