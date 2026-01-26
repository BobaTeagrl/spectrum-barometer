from flask import Flask

def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = 'changebeforerealeaseordie'
    
    from web.routes import bp
    app.register_blueprint(bp)
    
    return app