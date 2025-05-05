# run.py (at the project root, outside src)
import os
from src import create_app # Import the factory function

# Create the Flask app instance using the factory
# FLASK_CONFIG environment variable will determine which config is used (dev, prod, etc.)
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

if __name__ == '__main__':
    # Use Flask's built-in server - suitable for development
    # Host 0.0.0.0 makes it accessible outside container
    # Port can be configured via env var or default
    port = int(os.getenv('PORT', 5000))
    # Debug mode is controlled by the app's config (loaded from FLASK_CONFIG)
    app.run(host='0.0.0.0', port=port)