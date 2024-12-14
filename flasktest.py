import google.generativeai as genai

genai.configure(api_key="AIzaSyBUgj8tfSIasZMejyQwurSTDSLN3dTI__8")
model = genai.GenerativeModel("gemini-1.5-flash")
response = model.generate_content("Explain how AI works")
print(response.text)