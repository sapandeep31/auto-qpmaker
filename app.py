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

        prompt = f"""Generate a Government Exam Preparation Question Paper

Please generate a question paper based on the following specifications:

### Topics:  
- {chr(10).join('- ' + topic for topic in data['selected_topics'])}

### Parameters:  
1. **Number of Questions**: {data['num_questions']}  
2. **Difficulty Level**: {data['difficulty'].capitalize()}  
3. **Question Types**: {', '.join(data['question_types'])}  

### Language Requirements:  
- For each question, provide both **English and Kannada versions**.  
- Ensure there are **no grammatical or spelling errors** in either language.

### Formatting:  
1. **Number the questions sequentially** (1, 2, 3, etc.).  
2. For each question:
   - **English Question / Kannada Question**  
   - For options, use the format below, ensuring both languages are represented.

### Output Instructions:  
- Ensure proper spacing between questions and options for clarity.  
- The content should be in **plain text format** (no Markdown or HTML formatting).  
- Include a **mix of normal MCQs and the specified MCQ types**.

### Example Formats:

1. **Comprehension Based Questions**

   Passage: The human brain is the central organ of the nervous system. It controls various body functions. / ಮಾನವ ಮೆದುಳು ನರನಾಳದ ಕೇಂದ್ರ ಅಂಗವಾಗಿದೆ. ಇದು ವಿವಿಧ ದೇಹ ಕಾರ್ಯಗಳನ್ನು ನಿಯಂತ್ರಿಸುತ್ತದೆ.  
   Question: What is the role of the human brain? / ಮಾನವ ಮೆದುಳಿನ ಪಾತ್ರವೇನು?  
   a) It controls body movements. / ಇದು ದೇಹದ ಚಲನೆಗಳನ್ನು ನಿಯಂತ್ರಿಸುತ್ತದೆ.  
   b) It controls digestion. / ಇದು ದೀರ್ಘತೆಯನ್ನು ನಿಯಂತ್ರಿಸುತ್ತದೆ.  
   c) It controls memory. / ಇದು ನೆನಪನ್ನು ನಿಯಂತ್ರಿಸುತ್ತದೆ.  
   d) All of the above. / ಮೇಲ್ವಿಚಾರಣೆಯಾದ ಎಲ್ಲಾ.  

2. **Match the Following**

   **Column 1**:  
   1. Earth  
   2. Sun  
   3. Moon  
   4. Mars  

   **Column 2**:  
   a) Planet  
   b) Satellite  
   c) Star  
   d) Satellite of Earth  

   Match the correct pairs:  
   1 - c / 1 - ಸ  
   2 - a / 2 - ಅ  
   3 - b / 3 - ಬ  
   4 - d / 4 - ಡ  

3. **Assertion and Reasoning**

   Assertion: Water boils at 100°C. / ನೀರು 100°C ನಲ್ಲಿ ಓದುತ್ತದೆ.  
   Reasoning: This is the boiling point of water at standard atmospheric pressure. / ಇದು ಮಾನದಂಡ ವಾಯುಮಂಡಲ ಒತ್ತಡದಲ್ಲಿ ನೀರಿನ ಆಲಂಬ ನಕಲು ಬಿಂದುವಾಗಿದೆ.  
   a) Both assertion and reasoning are true, and reasoning explains assertion. / ಎರಡೂ ನಿರ್ಣಯ ಮತ್ತು ಕಾರಣ ಸರಿ, ಮತ್ತು ಕಾರಣ ನಿರ್ಣಯವನ್ನು ವಿವರಿಸುತ್ತದೆ.  
   b) Both assertion and reasoning are true, but reasoning does not explain assertion. / ಎರಡೂ ನಿರ್ಣಯ ಮತ್ತು ಕಾರಣ ಸರಿ, ಆದರೆ reasoning, assertion ಅನ್ನು ವಿವರಿಸುವುದಿಲ್ಲ.  
   c) Assertion is true, but reasoning is false. / Assertion ಸರಿ ಆದರೆ reasoning ತಪ್ಪಾಗಿದೆ.  
   d) Assertion is false, but reasoning is true. / Assertion ತಪ್ಪಾಗಿದೆ, reasoning ಸರಿ.  

4. **Statement and Conclusion**

   **Statement**: All birds can fly. / ಎಲ್ಲಾ ಹಕ್ಕಿಗಳು ಹಾರಬಹುದು.  
   **Conclusion**: A crow is a bird; therefore, it can fly. / ಕಾಗೆ ಹಕ್ಕಿಯಾಗಿದೆ, ಆದ್ದರಿಂದ ಅದು ಹಾರಬಹುದು.  
   a) Conclusion follows from the statement. / ನಿರ್ಣಯವು ಹೇಳಿಕೆಯಿಂದ ಅನುಸರಿಸುತ್ತದೆ.  
   b) Conclusion does not follow from the statement. / ನಿರ್ಣಯವು ಹೇಳಿಕೆಯಿಂದ ಅನುಸರಿಸುವುದಿಲ್ಲ.  
   c) Statement is false, and conclusion follows. / ಹೇಳಿಕೆ ತಪ್ಪಾಗಿದೆ, ಆದರೆ ನಿರ್ಣಯವು ಅನುಸರಿಸುತ್ತದೆ.  
   d) Both statement and conclusion are false. / ಹೇಳಿಕೆ ಮತ್ತು ನಿರ್ಣಯ ಎರಡೂ ತಪ್ಪಾಗಿದೆ.  

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