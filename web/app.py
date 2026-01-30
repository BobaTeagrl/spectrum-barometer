from flask import Flask
import atexit
import signal
import sys

def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = 'changebeforerealeaseordie'
    
    from web.routes import bp
    app.register_blueprint(bp)
    
    # cleanup monitoring on shutdown
    def cleanup():
        from barometer.background import stop_monitoring, is_monitoring
        if is_monitoring():
            stop_monitoring()
    
    atexit.register(cleanup)
    
    # handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    return app