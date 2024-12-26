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

        prompt = f"""Generate a Government Exam Preparation Question Bank

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

### Output Instructions:  
- Ensure proper spacing between questions and options for clarity.  
- The content should be in **plain text format** (no Markdown or HTML formatting).  
- Make questions on only specified MCQ type.

### Example Formats (NOTE: these are just example formats; make similar but unique questions, don't repeat these exact questions or options):

1. **Multiple Select Questions**

   Which of the following statements about the Indian Constitution are correct? / ಭಾರತೀಯ ಸಂವಿಧಾನದ ಕುರಿತು ಕೆಳಗಿನ ಯಾವ ಹೇಳಿಕೆಗಳು ಸರಿಯಾಗಿವೆ?

1)The Constitution of India was adopted on 26th January 1950. / ಭಾರತೀಯ ಸಂವಿಧಾನವನ್ನು 1950ರ ಜನವರಿ 26ರಂದು ಅಂಗೀಕರಿಸಲಾಯಿತು.  
2)The Preamble of the Constitution mentions India as a "Sovereign Socialist Secular Democratic Republic." / ಸಂವಿಧಾನದ ಮುನ್ನುಡಿಯಲ್ಲಿ ಭಾರತವನ್ನು "ಸಾರ್ವಭೌಮ ಸಮಾಜವಾದಿ ಧರ್ಮನಿರಪೇಕ್ಷ ಪ್ರಜಾಪ್ರಭುತ್ವ ಗಣರಾಜ್ಯ" ಎಂದು ಉಲ್ಲೇಖಿಸಲಾಗಿದೆ.  
3)The Fundamental Duties were part of the original Constitution. / ಮೂಲ ಸಂವಿಧಾನದಲ್ಲಿ ಮೂಲಭೂತ ಕರ್ತವ್ಯಗಳನ್ನು ಸೇರಿಸಲಾಗಿದೆ.  
4)Directive Principles of State Policy are non-justiciable in nature. / ರಾಜ್ಯತಂತ್ರದ ಮಾರ್ಗಸೂಚಿ ತತ್ವಗಳು ಕಾನೂನು ಸಮ್ಮತವಿಲ್ಲದವು.  
(a) 1 and 2 / 1 ಮತ್ತು 2  
(b) 2 and 3 / 2 ಮತ್ತು 3  
(c) 2 and 4 / 2 ಮತ್ತು 4  
(d) 1 and 4 / 1 ಮತ್ತು 4  
**Correct Answer**: (c) 2 and 4 / 2 ಮತ್ತು 4  

2. **Comprehension Based Questions**

   Passage: The human brain is the central organ of the nervous system. It controls various body functions. / ಮಾನವ ಮೆದುಳು ನರನಾಳದ ಕೇಂದ್ರ ಅಂಗವಾಗಿದೆ. ಇದು ವಿವಿಧ ದೇಹ ಕಾರ್ಯಗಳನ್ನು ನಿಯಂತ್ರಿಸುತ್ತದೆ.  
   Question: What is the role of the human brain? / ಮಾನವ ಮೆದುಳಿನ ಪಾತ್ರವೇನು?  
(a) It controls body movements. / ಇದು ದೇಹದ ಚಲನೆಗಳನ್ನು ನಿಯಂತ್ರಿಸುತ್ತದೆ.  
(b) It controls digestion. / ಇದು ದೀರ್ಘತೆಯನ್ನು ನಿಯಂತ್ರಿಸುತ್ತದೆ.  
(c) It controls memory. / ಇದು ನೆನಪನ್ನು ನಿಯಂತ್ರಿಸುತ್ತದೆ.  
(d) All of the above. / ಮೇಲ್ವಿಚಾರಣೆಯಾದ ಎಲ್ಲಾ.  
**Correct Answer**: (d) All of the above / ಮೇಲ್ವಿಚಾರಣೆಯಾದ ಎಲ್ಲಾ.  

3. **Match the Following**
Column 1 / ಕಾಲಮ್ 1:

Earth / ಭೂಮಿ
Sun / ಸೂರ್ಯ
Moon / ಚಂದ್ರ
Mars / ಮಂಗಳ
Column 2 / ಕಾಲಮ್ 2:
a) Planet / ಗ್ರಹ
b) Star / ನಕ್ಷತ್ರ
c) Natural Satellite / ನೈಸರ್ಗಿಕ ಉಪಗ್ರಹ
d) Red Planet / ಕೆಂಪು ಗ್ರಹ

(a) 1 - a, 2 - b, 3 - c, 4 - d / 1 - ಅ, 2 - ಬ, 3 - ಸಿ, 4 - ಡ
(b) 1 - b, 2 - a, 3 - d, 4 - c / 1 - ಬ, 2 - ಅ, 3 - ಡ, 4 - ಸಿ
(c) 1 - c, 2 - d, 3 - a, 4 - b / 1 - ಸಿ, 2 - ಡ, 3 - ಅ, 4 - ಬ
(d) 1 - a, 2 - c, 3 - d, 4 - b / 1 - ಅ, 2 - ಸಿ, 3 - ಡ, 4 - ಬ

Correct Answer:
(a) 1 - a, 2 - b, 3 - c, 4 - d / 1 - ಅ, 2 - ಬ, 3 - ಸಿ, 4 - ಡ 

4. **Assertion and Reasoning**

   Assertion: Water boils at 100°C. / ನೀರು 100°C ನಲ್ಲಿ ಓದುತ್ತದೆ.  
   Reasoning: This is the boiling point of water at standard atmospheric pressure. / ಇದು ಮಾನದಂಡ ವಾಯುಮಂಡಲ ಒತ್ತಡದಲ್ಲಿ ನೀರಿನ ಆಲಂಬ ನಕಲು ಬಿಂದುವಾಗಿದೆ.  
(a) Both assertion and reasoning are true, and reasoning explains assertion. / ಎರಡೂ ನಿರ್ಣಯ ಮತ್ತು ಕಾರಣ ಸರಿ, ಮತ್ತು ಕಾರಣ ನಿರ್ಣಯವನ್ನು ವಿವರಿಸುತ್ತದೆ.  
(b) Both assertion and reasoning are true, but reasoning does not explain assertion. / ಎರಡೂ ನಿರ್ಣಯ ಮತ್ತು ಕಾರಣ ಸರಿ, ಆದರೆ reasoning, assertion ಅನ್ನು ವಿವರಿಸುವುದಿಲ್ಲ.  
(c) Assertion is true, but reasoning is false. / Assertion ಸರಿ ಆದರೆ reasoning ತಪ್ಪಾಗಿದೆ.  
(d) Assertion is false, but reasoning is true. / Assertion ತಪ್ಪಾಗಿದೆ, reasoning ಸರಿ.  
**Correct Answer**: (a) Both assertion and reasoning are true, and reasoning explains assertion / ಎರಡೂ ನಿರ್ಣಯ ಮತ್ತು ಕಾರಣ ಸರಿ, ಮತ್ತು ಕಾರಣ ನಿರ್ಣಯವನ್ನು ವಿವರಿಸುತ್ತದೆ.  

5. **Statement and Conclusion**

   **Statement / ಹೇಳಿಕೆ**: All birds can fly. / ಎಲ್ಲಾ ಹಕ್ಕಿಗಳು ಹಾರಬಹುದು.  
   **Conclusion / ನಿರ್ಣಯ**: A crow is a bird; therefore, it can fly. / ಕಾಗೆ ಹಕ್ಕಿಯಾಗಿದೆ, ಆದ್ದರಿಂದ ಅದು ಹಾರಬಹುದು.  
(a) Conclusion follows from the statement. / ನಿರ್ಣಯವು ಹೇಳಿಕೆಯಿಂದ ಅನುಸರಿಸುತ್ತದೆ.  
(b) Conclusion does not follow from the statement. / ನಿರ್ಣಯವು ಹೇಳಿಕೆಯಿಂದ ಅನುಸರಿಸುವುದಿಲ್ಲ.  
(c) Statement is false, and conclusion follows. / ಹೇಳಿಕೆ ತಪ್ಪಾಗಿದೆ, ಆದರೆ ನಿರ್ಣಯವು ಅನುಸರಿಸುತ್ತದೆ.  
(d) Both statement and conclusion are false. / ಹೇಳಿಕೆ ಮತ್ತು ನಿರ್ಣಯ ಎರಡೂ ತಪ್ಪಾಗಿದೆ.  
**Correct Answer**: (a) Conclusion follows from the statement / ನಿರ್ಣಯವು ಹೇಳಿಕೆಯಿಂದ ಅನುಸರಿಸುತ್ತದೆ.  
"""

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
    app.run(debug=True)
