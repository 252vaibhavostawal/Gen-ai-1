#!/usr/bin/env python
import os
from app import create_app
from app.extensions import socketio

env = os.environ.get("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", 5000))
    print(f"\n==================================================================")
    print(f" Multimodal Attendance & Engagement Agent (Offline-First)")
    print(f" Running at: http://{host}:{port}")
    print(f" Default Instructor Account: instructor / admin123")
    print(f"==================================================================\n")
    socketio.run(app, host=host, port=port, debug=True, allow_unsafe_werkzeug=True)
