from flask import Flask, request, render_template
import os
import fitz  # PyMuPDF
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

def extract_footer_details_from_pdf(pdf_path):
    """Extracts the student name and Coursera URL from the certificate."""
    try:
        with fitz.open(pdf_path) as pdf:
            text = ""
            for page in pdf:
                text += page.get_text("text")
            
            # Handle multi-line URLs
            url_match = re.search(r'https?://coursera\.org/verify(?:/[A-Za-z0-9]+)?(?:/\S+)?', text.replace("\n", ""))
            url = url_match.group(0) if url_match else None
            
            name_match = re.search(r'(.+)\s+has successfully completed the online', text, re.IGNORECASE)
            name = name_match.group(1).strip() if name_match else None
            
            return name, url
    except Exception as e:
        print(f"Error processing PDF {pdf_path}: {e}")
        return None, None

def check_url_status(url, expected_name):
    """Checks if the URL is accessible and validates the name on the certificate webpage using Selenium."""
    try:
        options = Options()
        options.headless = True
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get(url)
        try:
            name_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//*[@id='rendered-content']/div/div/div[1]/div/div/div[2]/div[1]/div[1]/div/div[2]/h3/span/strong"))
            )
            name_from_web = name_element.text.strip()
        except Exception as e:
            print(f"Error finding name on webpage using XPath: {e}")
            name_from_web = None
        driver.quit()

        if name_from_web and expected_name and name_from_web.lower() == expected_name.lower():
            return "Verified"
        elif name_from_web:
            return f"Mismatch: Expected '{expected_name}', Found '{name_from_web}'"
        else:
            return "Name Not Found on Webpage"
    except Exception as e:
        print(f"Error accessing URL {url}: {e}")
        return "Error with Webpage or Selenium"

@app.route('/')
def upload_file():
    return render_template('index.html')

@app.route('/validate', methods=['POST'])
def validate():
    if 'file' not in request.files:
        return "No file uploaded", 400
    file = request.files['file']
    if file.filename == '':
        return "No file selected", 400
    
    pdf_path = os.path.join("uploads", file.filename)
    file.save(pdf_path)

    name, url = extract_footer_details_from_pdf(pdf_path)
    if url and name:
        status = check_url_status(url, name)
        os.remove(pdf_path)
        return f"Certificate Name: {name}<br>URL: {url}<br>Status: {status}"
    else:
        os.remove(pdf_path)
        return "Could not extract name or URL from the certificate."

if __name__ == '__main__':
    app.run(debug=True)
