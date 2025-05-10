from flask import Flask, request, jsonify, render_template
from transformers import GPTJForCausalLM, GPT2Tokenizer
import json, os, difflib

# Flask 앱 설정
app = Flask(__name__)

# 기본 설정
HISTORY_FILE = "memory.json"
ADMIN_PASSWORD = "seoan1024"
DEFAULT_MEMORY = {
    "안녕": "안녕하세요! 무엇을 도와드릴까요?",
    "오늘 날씨 어때?": "지역마다 다르지만, 대체로 맑거나 흐릴 수 있어요.",
    "고마워": "언제든지요!"
}

# 메모리 파일이 없으면 기본 메모리로 초기화
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(DEFAULT_MEMORY, f, ensure_ascii=False, indent=2)

# 메모리 파일 로드
with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
    memory = json.load(f)

vocab_list = list(DEFAULT_MEMORY.keys()) + ["정렬", "리스트", "파이썬", "기억", "검색", "챗봇", "날씨", "시간", "감사", "가격"]
last_response = ""

# GPT-J 모델 로드
model_name = "EleutherAI/gpt-j-6B"
model = GPTJForCausalLM.from_pretrained(model_name)
tokenizer = GPT2Tokenizer.from_pretrained(model_name)

# 오타 수정 함수
def correct_typo(user_input):
    return ' '.join([ 
        difflib.get_close_matches(w, vocab_list, n=1, cutoff=0.7)[0] if difflib.get_close_matches(w, vocab_list, n=1, cutoff=0.7) else w
        for w in user_input.split()
    ])

# 유사한 질문 찾기
def find_similar_question(user_input):
    for q in memory:
        if difflib.SequenceMatcher(None, user_input, q).ratio() > 0.75:
            return q
    return None

# GPT-J 모델을 사용하여 응답 생성
def generate_response(input_text):
    inputs = tokenizer(input_text, return_tensors="pt")
    output = model.generate(inputs["input_ids"], max_length=150, num_return_sequences=1, no_repeat_ngram_size=2)
    response = tokenizer.decode(output[0], skip_special_tokens=True)
    return response

# 메인 페이지 라우트
@app.route('/')
def index():
    return render_template("index.html")

# 채팅 기능 라우트
@app.route('/chat', methods=['POST'])
def chat():
    global last_response
    user_input = request.json['message']

    # 관리자 비밀번호 입력 시 메모리 반환
    if user_input.strip() == ADMIN_PASSWORD:
        reply = '\n'.join([f"Q: {q}\nA: {a}" for q, a in memory.items()])
    else:
        # 오타 수정
        corrected = correct_typo(user_input)

        # 유사한 질문이 있으면 기존 메모리에서 응답
        similar_q = find_similar_question(corrected)
        if similar_q:
            reply = memory[similar_q]
        else:
            # GPT-J 모델을 통해 새로운 응답 생성
            reply = generate_response(corrected)
            memory[corrected] = reply

            # 메모리 파일 업데이트
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(memory, f, ensure_ascii=False, indent=2)

    last_response = reply
    return jsonify({"reply": reply})

# 서버 실행
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
