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
app.secret_key = 'your_secret_key_here'

# Configure upload folder
app.config['UPLOAD_FOLDER'] = 'uploads'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    if username == 'test@g' and password == 'hi':
        session['logged_in'] = True
        return redirect(url_for('index'))
    else:
        return render_template('home.html', error='Invalid credentials')

@app.route('/index')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('home'))
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    return upload_file(app)

@app.route('/generate', methods=['POST'])
def generate():
    return generate_paper()

if __name__ == '__main__':
    app.run()
