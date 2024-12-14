from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import pdfplumber
import json
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# Configure upload folder
app.config['UPLOAD_FOLDER'] = 'uploads'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Configure Gemini API
genai.configure(api_key="AIzaSyBUgj8tfSIasZMejyQwurSTDSLN3dTI__8")
model = genai.GenerativeModel("gemini-1.5-flash")

@app.route('/')
def index():
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

        prompt = f"""Generate a question paper with the following specifications:

Topics:
{chr(10).join('- ' + topic for topic in data['selected_topics'])}

Parameters:
- Number of questions: {data['num_questions']}
- Difficulty level: {data['difficulty'].capitalize()}
- Question types: {', '.join(data['question_types'])}

Generate a complete govt exam prep level questions using ONLY the specified question types:

Requirements:
- Provide clear marking scheme
- Include answer key at the end
- Use proper markdown formatting
- Ensure questions are properly numbered
- Distribute questions evenly across topics
- Give proper line spacing between questions and line breaks after every mcq option and question
- every question is a mcq so they all will have a 4 options. and after before each option insert a line break

"""
        print('/n', prompt, '/n')
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