import os
import urllib3
import logging

urllib3.disable_warnings()

from flask import Flask, render_template, request, Response, redirect, url_for, session
import requests
from config.env import ACCOUNT_ID, TOKEN_ID, BASE_URL

app = Flask(__name__)
app.secret_key = os.urandom(24)


@app.route('/')
def hello_world():
    return render_template('index.html')

@app.errorhandler(Exception)
def handle_error(e):
    return render_template('error.html'), 500

@app.route('/Uploader', methods=['POST'])
def uploader():
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        return redirect(request.url)

    name = file.filename
    file.save(os.path.join("Images", name))

    with open('Images/' + name, 'rb') as f:
        image_data = f.read()
    image_to_text_url = (BASE_URL + '@cf/unum/uform-gen2-qwen-500m')
    image_to_text_headers = {
        'Content-Type': 'application/data-binary',
        'Authorization': 'Bearer ' + TOKEN_ID
    }
    r = requests.post(image_to_text_url, data=image_data, headers=image_to_text_headers, verify=False)

    text_summarization_url = (BASE_URL + '@cf/facebook/bart-large-cnn')
    to_be_summarized = r.json().get('result')['description']
    image_to_text_headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + TOKEN_ID
    }
    payload = {
        "input_text": to_be_summarized,
        "max_length": 1024
    }
    r_sum = requests.post(text_summarization_url, json=payload, headers=image_to_text_headers, verify=False)
    session['r_sum'] = r_sum.json()
    return redirect(url_for('selector'))


@app.route('/selector')
def selector():
    languages = ["English", "Spanish", "French", "Chinese", "Arabic", "Hindi", "Portuguese", "Russian", "German",
                 "Japanese"]
    questions = [
        {"id": "1", "name": "how i can make"},
        {"id": "2", "name": "calculate calories"},
        {"id": "3", "name": "what is the ingredients"},
        {"id": "4", "name": "question 1 & question 2"},
        {"id": "5", "name": "question 1 & question 3"},
        {"id": "6", "name": "question 2 & question 3"},
        {"id": "7", "name": "all question"},
    ]
    return render_template('selector.html', languages=languages, questions=questions)


@app.route('/result', methods=['POST'])
def result():

    text_generation_url = (BASE_URL+'@cf/openchat/openchat-3.5-0106')
    translated_text_url_model = (BASE_URL + '@cf/meta/m2m100-1.2b')

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + TOKEN_ID
    }

    classify_summary_json = session.get('r_sum')
    summary_text = classify_summary_json.get('result')['summary']
    selected_language = request.form['language']
    number_of_persons = request.form['number_of_persons']
    question_id = request.form['question']
    questions = [
        {"id": 1, "name": "give me steps to make ? " + summary_text},
        {"id": 2, "name": "give me calories in ? " + summary_text},
        {"id": 3, "name": "give me ingredients for " + number_of_persons + " persons from ? " + summary_text},
        {"id": 4, "name": "give me steps to make and  calculate calories in each step for ? " + summary_text},
        {"id": 5, "name": "give me steps to make and  give me ingredients for " + number_of_persons + " persons from ? " + summary_text},
        {"id": 6, "name": "give me calories and  give me ingredients for " + number_of_persons + " persons from ? " + summary_text},
        {"id": 7, "name": "give me steps to make and  give me ingredients for " + number_of_persons
                          + " persons from and give me calories in each item in ingredients ? " + summary_text},
    ]
    question = ''
    for q in questions:
        if q['id'] == int(question_id):
            question = q['name']
    #print(question)
    generation_payload = {
        "messages": [
            {"role": "system", "content": "You are a friendly assistant"},
            {"role": "user", "content": question}
        ]
    }
    text_generation_json = requests.post(text_generation_url, json=generation_payload,
                                                     headers=headers,
                                                     verify=False)
    question_answer = text_generation_json.json().get('result')['response']
    #print(question_answer)

    if selected_language != 'English':
        question_answer = question_answer.replace('\n', '')
        translated_text_payload = {
            "text": "in steps format " + question_answer,
            "source_lang": "english",
            "target_lang": selected_language.lower()
        }
        translated_text_json = requests.post(translated_text_url_model, json=translated_text_payload,
                                             headers=headers,
                                             verify=False)
        translated_text = translated_text_json.json().get('result')['translated_text']
        return render_template('result.html', question_answer_en=question_answer ,question_answer_not_en=translated_text , selected_language=selected_language)
    else:
        return render_template('result.html', question_answer_en=question_answer ,question_answer_not_en='', selected_languag='')

if __name__ == '__main__':
    app.run()
