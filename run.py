
#!/usr/bin/env python

import os

from app import create_app
from app.extensions import socketio


# Load the application environment
env = os.environ.get("FLASK_ENV", "production")

# Create the Flask application
app = create_app(env)


if __name__ == "__main__":
    # Render requires the app to listen on all network interfaces
    host = "0.0.0.0"

    # Render provides the port through the PORT environment variable
    port = int(os.environ.get("PORT", 10000))

    print("=" * 66)
    print("Multimodal Attendance & Engagement Agent")
    print(f"Running on {host}:{port}")
    print("=" * 66)

    # Start the Flask-SocketIO server
    socketio.run(
        app,
        host=host,
        port=port,
        debug=False,
        allow_unsafe_werkzeug=True
    )
