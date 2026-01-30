from flask import Flask
import atexit
import signal
import sys

def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = 'changebeforerealeaseordie'
    
    from web.routes import bp
    app.register_blueprint(bp)
    
    # Cleanup monitoring on shutdown ONLY if we own it
    def cleanup():
        from barometer.background import is_owned_by_current_process, stop_monitoring
        if is_owned_by_current_process():
            stop_monitoring()
    
    atexit.register(cleanup)
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    return app