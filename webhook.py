from flask import Flask, request
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests
import os
import logging
from datetime import datetime

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv('example.env')

# Configure logging
logging.basicConfig(filename='webhook_errors.log', level=logging.ERROR, format='%(asctime)s  %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Function to print issue information
def print_info(issue_number, translated_description, status, tracker, priority, assignee_name, assignee_lastname):
    print()
    print(f'Issue number is: {issue_number}')
    print(f"Issue description: {translated_description}")
    print(f"Issue status: {status}")
    print(f"Issue tracker: {tracker}")
    print(f"Issue priority: {priority}")
    print(f"Issue assignee: {assignee_name} {assignee_lastname}")
    print()

# Function to translate text to English
def translate_to_english(text):
    clean_text = BeautifulSoup(text, 'html.parser').get_text()
    translated_text = GoogleTranslator(source='auto', target='en').translate(clean_text)
    return translated_text

# Function to send WhatsApp message
def send_whatsapp_message(message):
    instance_id = os.getenv("INSTANCE_ID")
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    group_name = os.getenv("GROUP_NAME")
    group_admin = os.getenv("GROUP_ADMIN")

    headers = {
        'X-WM-CLIENT-ID': client_id,
        'X-WM-CLIENT-SECRET': client_secret
    }

    json_body = {
        'group_name': group_name,
        'group_admin': group_admin,
        'message': message
    }

    try:
        response = requests.post(f"http://api.whatsmate.net/v3/whatsapp/group/text/message/{instance_id}", headers=headers, json=json_body)
        response.raise_for_status()  # Raise an error for unsuccessful response status
        print("WhatsApp message sent successfully.")
    except Exception as e:
        # Log the error
        logging.error(f"Error sending WhatsApp message: {e}")

@app.route('/', methods=['POST', 'GET'])
def redmine_webhook():
    if request.method == 'POST':
        try:
            data = request.json
            issue_number = data.get('payload', {}).get('issue', {}).get('id')
            translated_description = translate_to_english(data.get('payload', {}).get('issue', {}).get('description', ''))
            status = data.get('payload', {}).get('issue', {}).get('status', {}).get('name')
            tracker = data.get('payload', {}).get('issue', {}).get('tracker', {}).get('name')
            priority = data.get('payload', {}).get('issue', {}).get('priority', {}).get('name')
            assignee_name = data.get('payload', {}).get('issue', {}).get('assignee', {}).get('firstname')
            assignee_lastname = data.get('payload', {}).get('issue', {}).get('assignee', {}).get('lastname')

            message = f'''Issue number: {issue_number}
Issue description: {translated_description}
Issue status: {status}
Issue tracker: {tracker}
Issue priority: {priority}
Issue assignee: {assignee_name} {assignee_lastname}'''

            send_whatsapp_message(message)

            return 'Webhook request successfully processed', 200
        except Exception as e:
            # Log the error
            logging.error(f"Error processing webhook request: {e}")
            return 'Internal Server Error', 500
    else:
        return 'Method Not Allowed', 405

if __name__ == '__main__':
    host = os.getenv("HOST")
    port = os.getenv("PORT")
    debug = os.getenv("DEBUG")

    app.run(host=host, port=port)
    app.run(debug=debug)