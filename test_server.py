from flask import Flask, request, jsonify

# Flask 앱 생성
app = Flask(__name__)

# "/api/publish" 주소로 POST 요청을 처리할 함수 정의
@app.route("/api/publish", methods=["POST"])
def handle_publish():
    # 데스크톱 앱이 보낸 JSON 데이터를 받음
    data = request.json

    # 서버의 터미널 창에 받은 데이터를 출력 (성공했는지 눈으로 확인!)
    print("--- 데이터 수신 성공! ---")
    print(f"프로젝트 이름: {data.get('projectName')}")
    print(f"아이템 개수: {data.get('itemCount')}")
    print("------------------------")

    # 데스크톱 앱으로 성공 메시지를 담은 JSON을 보냄
    return jsonify({"message": "데이터를 성공적으로 받았습니다!"}), 200

# 서버 실행
if __name__ == "__main__":
    print("테스트 서버가 http://127.0.0.1:5000 에서 실행 중입니다...")
    app.run(port=5000)