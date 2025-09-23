# test_server.py

import os
import json
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename # 파일 이름을 안전하게 처리하기 위해 import

# 업로드된 파일이 저장될 폴더
UPLOAD_FOLDER = 'uploads'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 서버 시작 시 uploads 폴더가 없으면 생성
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/api/publish", methods=["POST"])
def handle_publish():
    try:
        # --- 파일 처리 ---
        if 'pdf_file' not in request.files:
            return jsonify({"error": "PDF 파일이 없습니다."}), 400

        pdf_file = request.files['pdf_file']

        if pdf_file.filename == '':
            return jsonify({"error": "선택된 PDF 파일이 없습니다."}), 400

        # 파일 이름을 안전하게 만들고 저장 경로를 설정
        filename = secure_filename(pdf_file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        pdf_file.save(save_path)

        print(f"--- 파일 수신 및 저장 성공: {save_path} ---")

        # --- JSON 데이터 처리 ---
        # form 데이터로 전송된 JSON 문자열을 다시 딕셔너리로 변환
        project_data_str = request.form.get('project_data')
        project_data = json.loads(project_data_str)

        print("--- JSON 데이터 수신 성공! ---")
        print(f"프로젝트 이름: {project_data.get('projectName')}")
        items_received = project_data.get('items', [])
        print(f"수신한 아이템 개수: {len(items_received)}")
        print("--------------------------")

        response_message = f"파일 '{filename}'과 {len(items_received)}개의 아이템을 받았습니다!"
        return jsonify({"message": response_message}), 200

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": "서버 처리 중 오류 발생"}), 500

if __name__ == "__main__":
    print(f"테스트 서버가 http://127.0.0.1:5000 에서 실행 중입니다...")
    print(f"업로드된 파일은 '{UPLOAD_FOLDER}' 폴더에 저장됩니다.")
    app.run(port=5000, debug=True)