"""
AI-Powered Smart Meeting Analyzer & Decision Tracker
Main Flask Application - Entry Point
"""

import os
from flask import Flask, render_template
from flask_cors import CORS


def create_app():
    """Application factory pattern - clean and scalable."""
    app = Flask(__name__)

    # ── Configuration ──────────────────────────────────────────────────────────
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-me')
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB
    app.config['MONGO_URI'] = os.getenv('MONGO_URI', 'mongodb://localhost:27017/meeting_analyzer')

    # Allow cross-origin requests from the frontend
    CORS(app)

    # ── Ensure upload directory exists ─────────────────────────────────────────
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ── Register route blueprints ──────────────────────────────────────────────
    from routes.meeting_routes import meeting_bp
    from routes.analysis_routes import analysis_bp
    app.register_blueprint(meeting_bp, url_prefix='/api')
    app.register_blueprint(analysis_bp, url_prefix='/api')

    # ── Frontend route (serves the SPA) ───────────────────────────────────────
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/dashboard')
    def dashboard():
        return render_template('dashboard.html')

    return app


if __name__ == '__main__':
    application = create_app()
    print("🚀  Meeting Analyzer running → http://localhost:5000")
    application.run(debug=True, host='0.0.0.0', port=5000)
