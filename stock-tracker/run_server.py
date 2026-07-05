import sys
sys.path.insert(0, '.')
from web.app import create_app
app = create_app()
app.run(port=5000)
