from flask import Flask, render_template, redirect, url_for, session, request
from flask_cors import CORS
from dotenv import load_dotenv
from pymongo import MongoClient
import os

# Importing functions
from processupload import upload_file
from generatequestions import generate_paper

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Set a secret key for session management
app.secret_key = os.getenv('SECRET_KEY')

# Configure session cookie settings
app.config['SESSION_COOKIE_SECURE'] = True  # Ensures cookies are only sent over HTTPS
app.config['SESSION_PERMANENT'] = False  # Session cookies expire when the browser is closed

# Configure upload folder
app.config['UPLOAD_FOLDER'] = 'uploads'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI')  # Connection string from .env
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["users"]  # Database name
users_collection = db["users"]  # Collection name

@app.route('/')
def home():
    """Render the login page."""
    return render_template('home.html')

@app.route('/login', methods=['POST'])
def login():
    """Handle user login."""
    username = request.form.get('username')
    password = request.form.get('password')

    # Fetch user from MongoDB
    user = users_collection.find_one({"username": username, "password": password})

    if user:
        session['logged_in'] = True
        session['username'] = username
        return redirect(url_for('index'))
    else:
        return render_template('home.html', error='Invalid credentials')

@app.route('/logout')
def logout():
    """Log out the user by clearing the session."""
    session.clear()
    return redirect(url_for('home'))

@app.route('/index')
def index():
    """Render the main index page."""
    if not session.get('logged_in'):
        return redirect(url_for('home'))
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    """Handle file uploads."""
    if not session.get('logged_in'):
        return redirect(url_for('home'))
    return upload_file(app)

@app.route('/generate', methods=['POST'])
def generate():
    """Generate a question paper."""
    if not session.get('logged_in'):
        return redirect(url_for('home'))
    return generate_paper()

@app.route('/users', methods=['GET'])
def get_users():
    """Fetch all users from the MongoDB collection."""
    if not session.get('logged_in'):
        return redirect(url_for('home'))
    try:
        users = list(users_collection.find({}, {"_id": 0}))  # Exclude MongoDB's default _id field
        return {"users": users}, 200
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/users', methods=['POST'])
def add_user():
    """Add a new user to the MongoDB collection."""
    if not session.get('logged_in'):
        return redirect(url_for('home'))
    try:
        user_data = request.json  # Expecting JSON data in the request body
        if not user_data:
            return {"error": "No user data provided"}, 400

        # Insert user into MongoDB
        users_collection.insert_one(user_data)
        return {"message": "User added successfully"}, 201
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == '__main__':
    # Ensure Flask listens on all network interfaces
    app.run(host='0.0.0.0', port=5000)

