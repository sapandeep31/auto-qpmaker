import os
import json
import pdfplumber
from flask import request, jsonify
from werkzeug.utils import secure_filename
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key = os.getenv('GENAI_API_KEY'))

def upload_file(app):
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
                    "English Topic Name/Kannada Topic Name (if you are taking out topic names, dont take it out without context, for example, if a topic name is 'downfall' then from previous topic or the same chapter take out as downfall of 'the thing'-- I MEAN TOPICS WITH CONTEXT)",
                    ...
                ]
            }}
            
            Syllabus text:
            {text}
            """

            result = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)

            cleaned_text = result.text.strip()
            if cleaned_text.startswith('```'):
                parts = cleaned_text.split('```')
                if len(parts) >= 3:
                    cleaned_text = parts[1]
                if cleaned_text.startswith('json'):
                    cleaned_text = cleaned_text[4:]
                cleaned_text = cleaned_text.strip()

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
