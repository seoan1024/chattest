
from flask import Flask, request, jsonify, render_template
import json, os, difflib
from duckduckgo_search import DDGS

app = Flask(__name__)

HISTORY_FILE = "memory.json"
ADMIN_PASSWORD = "seoan1024"
DEFAULT_MEMORY = {
    "안녕": "안녕하세요! 무엇을 도와드릴까요?",
    "오늘 날씨 어때?": "지역마다 다르지만, 대체로 맑거나 흐릴 수 있어요.",
    "고마워": "언제든지요!"
}

if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(DEFAULT_MEMORY, f, ensure_ascii=False, indent=2)

with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
    memory = json.load(f)

vocab_list = list(DEFAULT_MEMORY.keys()) + ["정렬", "리스트", "파이썬", "기억", "검색", "챗봇", "날씨", "시간", "감사", "가격"]
last_response = ""

def correct_typo(user_input):
    return ' '.join([
        difflib.get_close_matches(w, vocab_list, n=1, cutoff=0.7)[0] if difflib.get_close_matches(w, vocab_list, n=1, cutoff=0.7) else w
        for w in user_input.split()
    ])

def find_similar_question(user_input):
    for q in memory:
        if difflib.SequenceMatcher(None, user_input, q).ratio() > 0.75:
            return q
    return None

def search_web(query):
    with DDGS() as ddgs:
        results = list(ddgs.text(query, region='wt-wt', safesearch='Moderate', max_results=1))
        if results:
            body = results[0].get('body', '')
            url = results[0].get('href', '')
            if body:
                return f"{body} (출처: {url})" if url else body
    return ""

def summarize_text(text):
    sentences = text.split('.')
    important = [s.strip() for s in sentences if len(s.strip()) > 20]
    return '.'.join(important[:2]) + '.' if important else ''

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/chat', methods=['POST'])
def chat():
    global last_response
    user_input = request.json['message']
    if user_input.strip() == ADMIN_PASSWORD:
        reply = '\n'.join([f"Q: {q}\nA: {a}" for q, a in memory.items()])
    elif "요약" in user_input:
        reply = summarize_text(last_response)
    else:
        corrected = correct_typo(user_input)
        similar_q = find_similar_question(corrected)
        if similar_q:
            reply = memory[similar_q]
        else:
            web_info = search_web(corrected)
            summary = summarize_text(web_info) if web_info else "죄송해요, 잘 모르겠어요."
            source = web_info.split(' (출처: ')[-1] if '출처:' in web_info else ''
            reply = summary + (f"\n\n출처: {source}" if source else '')
            memory[corrected] = reply
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(memory, f, ensure_ascii=False, indent=2)
    last_response = reply
    return jsonify({ "reply": reply })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
