from flask import Flask, request
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup
import requests

app = Flask(__name__)

def printInfo(issue_number, translated_description, status, tracker, priority, assigneeName, assigneeLastname):

    print()
    print(f'Issue number is: {issue_number}')
    print(f"Issue description: {translated_description}")
    print(f"Issue status: {status}")
    print(f"Issue tracker: {tracker}")
    print(f"Issue priority: {priority}")
    print(f"Issue assignee: {assigneeName} {assigneeLastname}")
    print()

def translate_issue_to_english(data, data1, data2, data3):
    
    title = data[data1][data2][data3]

    clean_description = BeautifulSoup(title, 'html.parser').get_text()

    translated_title = GoogleTranslator(source='auto', target='en').translate(clean_description)

    return translated_title

def messageWhatsapp(mess):

    instanceId = "34"
    clientId = "it@bct.lv"
    clientSecret = "5199b1824e9b410da229bc46c3fe3fe1"

    groupName = 'BCT maintenance'
    groupAdmin = "37122300305"
    message = mess

    headers = {
        'X-WM-CLIENT-ID': clientId, 
        'X-WM-CLIENT-SECRET': clientSecret
    }

    jsonBody = {
        'group_name': groupName,
        'group_admin': groupAdmin,
        'message': message
    }

    r = requests.post("http://api.whatsmate.net/v3/whatsapp/group/text/message/%s" % instanceId, 
        headers=headers,
        json=jsonBody)

    print("Status code: " + str(r.status_code))
    print("RESPONSE : " + str(r.content))

@app.route('/', methods=['POST', 'GET']) 
def redmine_webhook():

    if request.method == 'POST':
        
        data = request.json
        # print(data)
        
        issue_number = data['payload']['issue']['id']
        translated_description = translate_issue_to_english(data, 'payload', 'issue', 'description')
        status = data['payload']['issue']['status']['name']
        tracker = data['payload']['issue']['tracker']['name']
        priority = data['payload']['issue']['priority']['name']
        assigneeName = data['payload']['issue']['assignee']['firstname']
        assigneeLastname = data['payload']['issue']['assignee']['lastname']

        # printInfo(issue_number, translated_description, status, tracker, priority, assigneeName, assigneeLastname)

        mess = f'''
        Issue number: {issue_number}
        Issue description: {translated_description}
        Issue status: {status}
        Issue tracker: {tracker}
        Issue priority: {priority}
        Issue assignee: {assigneeName} {assigneeLastname}
        '''

        messageWhatsapp(mess)

        return 'Вебхук запрос успешно обработан', 200
    
    else: return 'Метод не разрешен', 405
    
if __name__ == '__main__':
    app.run(host='172.25.29.149')
    app.run(debug=True)