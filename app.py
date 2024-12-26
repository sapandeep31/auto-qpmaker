from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import pdfplumber
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app)

# Set a secret key for session management
app.secret_key = 'your_secret_key_here'  

# Configure upload folder
app.config['UPLOAD_FOLDER'] = 'uploads'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Configure Gemini API
genai.configure(api_key = os.getenv('GENAI_API_KEY'))
model = genai.GenerativeModel("gemini-1.5-flash")

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Hardcoded login for now
    if username == 'test@g' and password == 'hi':
        session['logged_in'] = True
        return redirect(url_for('index'))
    else:
        return render_template('home.html', error='Invalid credentials')

@app.route('/index')
def index():
    # Check if user is logged in
    if not session.get('logged_in'):
        return redirect(url_for('home'))
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if file and file.filename.endswith('.pdf'):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                text = ""
                with pdfplumber.open(filepath) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() + "\n"

                if not text.strip():
                    return jsonify({'error': 'Failed to extract text from PDF'}), 400

                prompt = f"""Extract units or topics or chapters from the following syllabus text and return both English/Kannada names where applicable. 
                Return in JSON format with NO code formatting or backticks and enclose elements with double quotes in json.
                Use this schema:
                {{
                    "topics": [
                        "English Topic Name/Kannada Topic Name",
                        ...
                    ]
                }}
                
                Syllabus text:
                {text}
                """

                result = model.generate_content(prompt)
                
                # Clean the response text
                cleaned_text = result.text.strip()
                
                # Remove code block markers if they exist
                if cleaned_text.startswith('```'):
                    # Split by ``` and take the content
                    parts = cleaned_text.split('```')
                    # Get the middle part (the actual JSON)
                    if len(parts) >= 3:
                        cleaned_text = parts[1]
                    # If it starts with 'json', remove it
                    if cleaned_text.startswith('json'):
                        cleaned_text = cleaned_text[4:]
                    cleaned_text = cleaned_text.strip()

                # Parse the cleaned JSON
                topics_data = json.loads(cleaned_text)
                
                os.remove(filepath)
                return jsonify({
                    'success': True,
                    'topics': topics_data['topics']
                })

            except Exception as e:
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({'error': f'Processing error: {str(e)}'}), 500

        else:
            return jsonify({'error': 'Invalid file type. Please upload a PDF.'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate', methods=['POST'])
def generate_paper():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        required = ['selected_topics', 'num_questions', 'difficulty', 'question_types']
        if not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400

        prompt = f'''Generate a Government Exam Preparation Question Bank

Please generate questions based on the following specifications:

### Topics:
- {chr(10).join('- ' + topic for topic in data['selected_topics'])}

### Parameters:
1. **Number of Questions**: {data['num_questions']}
2. **Difficulty Level**: {data['difficulty'].capitalize()}
3. **Question Type**: {', '.join(data['question_types'])}

### Language Requirements:
- For each question, provide both **English and Kannada versions**.
- Ensure there are **no grammatical or spelling errors** in either language.

### Formatting:
1. Do not number the questions.
2. For each question:
   - **English Question / Kannada Question**
   - For options, use the format below, ensuring both languages are represented.
   - Correct Answer should also be mentioned before the next question.
3. Ensure variety in the correct answers and options for each question type.
4. Incorporate logical and conceptual variations to avoid repetitive patterns.

### Question Types and Guidelines:

1. **Normal MCQs**  
   Frame normal direct questions with four distinct options.  
   Example:  
   Who is the President of India? / ಭಾರತದ ಅಧ್ಯಕ್ಷರು ಯಾರು?  
   (a) Narendra Modi / ನರೇಂದ್ರ ಮೋದಿ  
   (b) Ram Nath Kovind / ರಾಮನಾಥ್ ಕೋವಿಂದ್  
   (c) Droupadi Murmu / ದ್ರೌಪದಿ ಮುರ್ಮು  
   (d) Pratibha Patil / ಪ್ರತಿಭಾ ಪಾಟೀಲ್  
   **Correct Answer**: (c) Droupadi Murmu / ದ್ರೌಪದಿ ಮುರ್ಮು  

2. **Multiple Select Questions**  
   Frame questions that have two or more correct answers. Ensure that correct options vary and are distributed logically.  
   Example:  
   Which of the following are Union Territories of India? / ಕೆಳಗಿನವುಗಳಲ್ಲಿ ಯಾವವು ಭಾರತದ ಕೇಂದ್ರಾಡಳಿತ ಪ್ರದೇಶಗಳಾಗಿವೆ?  
   (a) Delhi / ದೆಹಲಿ  
   (b) Chandigarh / ಚಂಡೀಗಡ  
   (c) Kerala / ಕೇರಳ  
   (d) Puducherry / ಪುದುಚೇರಿ  
   **Correct Answer**: (a) Delhi / ದೆಹಲಿ, (b) Chandigarh / ಚಂಡೀಗಡ, (d) Puducherry / ಪುದುಚೇರಿ  

3. **Comprehension-Based Questions**  
   Provide a short passage followed by relevant questions. Ensure options are conceptual and connected to the passage.  
   Example:  
   Passage: "The Indian economy is one of the fastest-growing economies in the world." / "ಭಾರತೀಯ ಆರ್ಥಿಕತೆಯು ವಿಶ್ವದ ವೇಗವಾಗಿ ಬೆಳೆಯುತ್ತಿರುವ ಆರ್ಥಿಕತೆಗಳಲ್ಲಿ ಒಂದಾಗಿದೆ."  
   Question: What is the Indian economy known for? / ಭಾರತೀಯ ಆರ್ಥಿಕತೆ ಏನಿಗಾಗಿ ಪ್ರಸಿದ್ಧವಾಗಿದೆ?  
   (a) Being stagnant / ಸ್ಥಗಿತವಾಗಿರುವ  
   (b) Fast growth / ವೇಗವಾಗಿ ಬೆಳೆಯುವುದು  
   (c) Decline in industries / ಕೈಗಾರಿಕೆಗಳಲ್ಲಿ ಕುಸಿತ  
   (d) Inflation control / ದರೇಹಿಚೆ ನಿಗ್ರಹ  
   **Correct Answer**: (b) Fast growth / ವೇಗವಾಗಿ ಬೆಳೆಯುವುದು  

4. **Match the Following**  
   Provide two columns with related elements and ask to match them. Ensure pairs vary and options are shuffled logically.  
   Example:  
   Column 1 / ಕಾಲಮ್ 1:  
   Earth / ಭೂಮಿ  
   Sun / ಸೂರ್ಯ  
   Moon / ಚಂದ್ರ  
   Mars / ಮಂಗಳ  
   Column 2 / ಕಾಲಮ್ 2:  
   (a) Planet / ಗ್ರಹ  
   (b) Star / ನಕ್ಷತ್ರ  
   (c) Natural Satellite / ನೈಸರ್ಗಿಕ ಉಪಗ್ರಹ  
   (d) Red Planet / ಕೆಂಪು ಗ್ರಹ  
   **Correct Answer**: (a) 1-a, 2-b, 3-c, 4-d / 1-ಅ, 2-ಬ, 3-ಸಿ, 4-ಡ  

5. **Assertion and Reasoning**  
   Frame questions with an assertion and reasoning statement, ensuring logical alignment between them.  
   Example:  
   Assertion: The Earth revolves around the Sun. / ಭೂಮಿ ಸೂರ್ಯನ ಸುತ್ತಲು ಸುತ್ತುತ್ತದೆ.  
   Reasoning: The Earth follows an elliptical orbit. / ಭೂಮಿ ಎಲಿಪ್ಟಿಕಲ್ ಕಕ್ಷೆಯನ್ನು ಅನುಸರಿಸುತ್ತದೆ.  
   (a) Both assertion and reasoning are true, and reasoning explains assertion. / ಎರಡೂ ನಿರ್ಣಯ ಮತ್ತು ಕಾರಣ ಸರಿ, ಮತ್ತು ಕಾರಣ ನಿರ್ಣಯವನ್ನು ವಿವರಿಸುತ್ತದೆ.  
   (b) Both assertion and reasoning are true, but reasoning does not explain assertion. / ಎರಡೂ ನಿರ್ಣಯ ಮತ್ತು ಕಾರಣ ಸರಿ, ಆದರೆ ಕಾರಣ ನಿರ್ಣಯವನ್ನು ವಿವರಿಸುವುದಿಲ್ಲ.  
   (c) Assertion is true, but reasoning is false. / ನಿರ್ಣಯ ಸರಿ ಆದರೆ ಕಾರಣ ತಪ್ಪಾಗಿದೆ.  
   (d) Assertion is false, but reasoning is true. / ನಿರ್ಣಯ ತಪ್ಪಾಗಿದೆ, ಆದರೆ ಕಾರಣ ಸರಿ.  
   **Correct Answer**: (a) Both assertion and reasoning are true, and reasoning explains assertion / ಎರಡೂ ನಿರ್ಣಯ ಮತ್ತು ಕಾರಣ ಸರಿ, ಮತ್ತು ಕಾರಣ ನಿರ್ಣಯವನ್ನು ವಿವರಿಸುತ್ತದೆ.  

6. **Statement and Conclusion**  
   Frame logical reasoning questions with a statement and a conclusion. Ensure variety in logical challenges.  
   Example:  
   Statement: All mammals have lungs. / ಎಲ್ಲಾ ಸಸ್ತನಿಗಳು ಶ್ವಾಸಕೋಶಗಳನ್ನು ಹೊಂದಿವೆ.  
   Conclusion: A whale is a mammal; therefore, it has lungs. / ತಿಮಿಂಗಿಲವು ಸಸ್ತನಿಯಾಗಿದೆ, ಆದ್ದರಿಂದ ಅದು ಶ್ವಾಸಕೋಶಗಳನ್ನು ಹೊಂದಿದೆ.  
   (a) Conclusion follows from the statement. / ನಿರ್ಣಯವು ಹೇಳಿಕೆಯಿಂದ ಅನುಸರಿಸುತ್ತದೆ.  
   (b) Conclusion does not follow from the statement. / ನಿರ್ಣಯವು ಹೇಳಿಕೆಯಿಂದ ಅನುಸರಿಸುವುದಿಲ್ಲ.  
   (c) Statement is false, and conclusion follows. / ಹೇಳಿಕೆ ತಪ್ಪಾಗಿದೆ, ಆದರೆ ನಿರ್ಣಯವು ಅನುಸರಿಸುತ್ತದೆ.  
   (d) Both statement and conclusion are false. / ಹೇಳಿಕೆ ಮತ್ತು ನಿರ್ಣಯ ಎರಡೂ ತಪ್ಪಾಗಿದೆ.  
   **Correct Answer**: (a) Conclusion follows from the statement / ನಿರ್ಣಯವು ಹೇಳಿಕೆಯಿಂದ ಅನುಸರಿಸುತ್ತದೆ.  

### Output Instructions:
- Ensure proper spacing between questions and options for clarity.
- The content should be in **plain text format** (no Markdown or HTML formatting).
- Ensure diverse framing of questions with logical and conceptual variety.
'''



        result = model.generate_content(prompt)
        if not result or not result.text:
            return jsonify({'error': 'Failed to generate questions'}), 500
        return jsonify({
            'success': True,
            'qp': result.text
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run()
