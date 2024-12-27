from flask import Flask, render_template, redirect, url_for, session, request
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Importing functions
from processupload import upload_file
from generatequestions import generate_paper

load_dotenv()

app = Flask(__name__)
CORS(app)

# Set a secret key for session management
app.secret_key = os.getenv('SECRET_KEY')

# Configure upload folder
app.config['UPLOAD_FOLDER'] = 'uploads'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Define protected routes
PROTECTED_ROUTES = ['/index', '/upload', '/generate']

@app.before_request
def require_login():
    """Redirect to login page if the user is not logged in."""
    if request.path in PROTECTED_ROUTES and not session.get('logged_in'):
        return redirect(url_for('home'))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    if username == os.getenv('USER_NAME') and password == os.getenv('PASSWORD'):
        session['logged_in'] = True
        return redirect(url_for('index'))
    else:
        return render_template('home.html', error='Invalid credentials')

@app.route('/logout')
def logout():
    """Log the user out and redirect to home."""
    session.pop('logged_in', None)
    return redirect(url_for('home'))

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    return upload_file(app)

@app.route('/generate', methods=['POST'])
def generate():
    return generate_paper()

@app.after_request
def prevent_caching(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.set_cookie('session', '', expires=0, samesite='Strict')  
    return response

if __name__ == '__main__':
    app.run()
