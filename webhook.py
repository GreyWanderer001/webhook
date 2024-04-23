from selenium.webdriver.chrome.options import Options

try:
    from googletrans import Translator
    TRANSLATION_AVAILABLE = True
except Exception:
    TRANSLATION_AVAILABLE = False

from flask import Flask, request
from selenium import webdriver
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from pathlib import Path
import requests
import logging
import shutil
import base64
import os

app = Flask(__name__)

load_dotenv('.env')
logging.basicConfig(filename='info.log', level=logging.INFO, format='%(asctime)s  %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


def print_info(issue_number, translated_description, status, tracker, priority, assignee_name, assignee_lastname):
    print()
    print(f'Issue number is: {issue_number}')
    print(f"Issue description: {translated_description}")
    print(f"Issue status: {status}")
    print(f"Issue tracker: {tracker}")
    print(f"Issue priority: {priority}")
    print(f"Issue assignee: {assignee_name} {assignee_lastname}")
    print()


def take_screenshot(save_path):
    try:
        url = os.getenv("URL")

        chromium = os.getenv("CHROMIUM")

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument("--window-size=1024,800")
        options.binary_location = chromium

        driver = webdriver.Chrome(options=options)
        driver.get(url)
        driver.save_screenshot(save_path)
        logging.info(f'Screenshot saved: {save_path}')
        driver.quit()

        if save_path.exists():
            logging.info(f"Screenshot already exists: {save_path}")
            return True
        
        logging.error(f"Error saving screenshoti {save_path}")

    except Exception as e:
        logging.exception(f"Error taking screenshot: {e}")
    
    return False


def get_foto(issue_id, folder_name):
    try:
        key = os.getenv("KEY")
        redmine_url = os.getenv("REDMINE_URL")

        url = f"{redmine_url}/issues/{issue_id}.json?include=attachments"
        response = requests.get(url, params={'key': key})
        response.raise_for_status()

        json_data = response.json()
        attachments = json_data['issue']['attachments']
        images = []

        for attachment in attachments:
            if attachment['content_type'].startswith('image'):
                image_url = attachment['content_url']

                image_response = requests.get(image_url, params={'key': key})
                image_response.raise_for_status()
                image_filename = folder_name.joinpath(f"image_{len(images) + 1}_{issue_id}.png").resolve()

                with open(image_filename, 'wb') as image_file:
                    image_file.write(image_response.content)

                print(f"Image {image_filename} downloaded successfully.")
                send_whatsapp_image(image_filename)
                images.append(image_filename.name)

        return images

    except Exception as e:
        logging.exception(f"Error getting images: {e}")
    
    return None


def send_translated(translated_description, issue_id):
    if not TRANSLATION_AVAILABLE:
        return

    try:
        key = os.getenv("KEY")
        redmine_url = os.getenv("REDMINE_URL")

        url = f"{redmine_url}/issues/{issue_id}.json"

        response = requests.get(url, params={'key': key})
        response.raise_for_status()
        issue_data = response.json()

        issue_data['issue']['custom_fields'] = [
            {
                "id": 2,
                "name": "Actual start time",
                "value": ""
            },
            {
                "id": 3,
                "name": "Actual end time",
                "value": ""
            },
            {
                "id": 6,
                "name": "Tehnikas vadītājs",
                "value": ""
            },
            {
                "id": 12,
                "name": "Translated Subject ",
                "value": translated_description
            }
        ]

        response = requests.put(url, params={'key': key}, json=issue_data)
        response.raise_for_status()
        print(f"Translated description sent successfully for issue {issue_id}.")

    except Exception as e:
        logging.error(f"Error sending translated description: {e}")


def translate_to_english(text):
    if not TRANSLATION_AVAILABLE:
        return text

    try:
        clean_text = BeautifulSoup(text, 'html.parser').get_text()

        translator = Translator()
        translation = translator.translate(clean_text)
        return translation.text
    
    except Exception as e:
        logging.exception(f"Error translating text: {e}")
    
    return text


def send_whatsapp_image(image):
    try:
        instance_id = os.getenv("INSTANCE_ID")
        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")
        group_name = os.getenv("GROUP_NAME")

        fullpath_to_photo = image
        image_base64 = None
        with open(fullpath_to_photo, 'rb') as image:
            image_base64 = base64.b64encode(image.read())

        headers = {
            'X-WM-CLIENT-ID': client_id,
            'X-WM-CLIENT-SECRET': client_secret
        }

        jsonBody = {
            'group_name': group_name,
            'image': image_base64.decode("utf-8"),
        }

        response = requests.post(f"http://api.whatsmate.net/v3/whatsapp/group/image/message/{instance_id}", headers=headers, json=jsonBody)
        response.raise_for_status()
        print("WhatsApp image sent successfully.")

    except Exception as e:
        logging.exception(f"Error sending WhatsApp image: {e}")


def send_whatsapp_message(message):
    try:
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

        response = requests.post(f"http://api.whatsmate.net/v3/whatsapp/group/text/message/{instance_id}", headers=headers, json=json_body)
        response.raise_for_status()
        print("WhatsApp message sent successfully.")

    except Exception as e:
        logging.exception(f"Error sending WhatsApp message: {e}")


@app.route('/', methods=['POST', 'GET'])
def redmine_webhook():
    if request.method == 'POST':
        try:
            data = request.json
            issue_id = data.get('payload', {}).get('issue', {}).get('id')

            folder_name = Path(f"request_{issue_id}")
            folder_name.mkdir(parents=True, exist_ok=True)

            issue_number = data.get('payload', {}).get('issue', {}).get('project').get('name')
            translated_description = translate_to_english(data.get('payload', {}).get('issue', {}).get('subject', ''))
            created = data.get('payload', {}).get('issue', {}).get('created_on', {})
            priority = data.get('payload', {}).get('issue', {}).get('priority', {}).get('name')
            assignee_name = data.get('payload', {}).get('issue', {}).get('author', {}).get('firstname')
            assignee_lastname = data.get('payload', {}).get('issue', {}).get('author', {}).get('lastname')

            created = created.replace('T', ' ')
            created = created.replace('Z', ' ')
            for i in range(5):
                created = created[:-1]

            if priority == 'Ir pieejama':
                priority = 'In action'
            else:
                priority = 'Out of action'

            message = f'''New issue added for: {issue_number}

Issue description:
{translated_description.upper()}

{issue_number} {priority}

Issue created:
{created}
Issue reporter: {assignee_name} {assignee_lastname}'''

            for item in data["payload"]["issue"]["custom_field_values"]:
                if item["custom_field_name"] == "Translated Subject" and item["value"] == "":
                    send_translated(translated_description, issue_id)
                    send_whatsapp_message(message)
                    get_foto(issue_id, folder_name)

                    if priority == 'Out of action':
                        screenshot = folder_name.joinpath(f'screenshot_{issue_id}.png')
                        if take_screenshot(screenshot):
                            send_whatsapp_image(screenshot)

            if folder_name.exists() and folder_name.is_dir():
                shutil.rmtree(folder_name)
                
                print(f"Folder {folder_name} deleted after processing the request.")

            return 'Webhook request successfully processed', 200
        except Exception as e:
            logging.exception(f"Error processing webhook request: {e}")
            return 'Internal Server Error', 500
    else:
        return 'Method Not Allowed', 405


if __name__ == '__main__':
    host = os.getenv("HOST")
    port = os.getenv("PORT")
    debug = os.getenv("DEBUG")

    app.run(host=host, port=port)
    app.run(debug=debug)
