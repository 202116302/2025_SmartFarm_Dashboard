from flask import Flask, render_template_string
import requests

app = Flask(__name__)

# HTML 템플릿
template = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>생태와 환경 스마트팜 물주기</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            text-align: center;
            color: #2c3e50;
            margin-bottom: 30px;
        }
        .group {
            margin: 20px 0;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
            background-color: #fafafa;
        }
        .group h3 {
            margin: 0 0 15px 0;
            color: #34495e;
        }
        .button-container {
            display: flex;
            gap: 10px;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s;
        }
        .btn-on {
            background-color: #27ae60;
            color: white;
        }
        .btn-on:hover {
            background-color: #219a52;
        }
        .btn-off {
            background-color: #e74c3c;
            color: white;
        }
        .btn-off:hover {
            background-color: #c0392b;
        }
        .status {
            margin-left: 20px;
            font-size: 14px;
            color: #7f8c8d;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌱 생태와 환경 스마트팜 물주기</h1>

        {% for i in range(1, 9) %}
        <div class="group">
            <h3>{{ i }}조 화분 물주기</h3>
            <div class="button-container">
                <a href="http://192.168.0.10{{ i }}/relay/on" class="btn btn-on" target="_blank">
                    💧 물주기 ON
                </a>
                <a href="http://192.168.0.10{{ i }}/relay/off" class="btn btn-off" target="_blank">
                    ⏹️ 물주기 OFF
                </a>
                <span class="status">IP: 192.168.0.10{{ i }}</span>
            </div>
        </div>
        {% endfor %}

        <div style="text-align: center; margin-top: 30px; color: #95a5a6;">
            <p>💡 버튼을 클릭하면 해당 장치로 직접 명령이 전송됩니다</p>
        </div>
    </div>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(template)


@app.route('/control/<int:group>/<action>')
def control_relay(group, action):
    """
    선택사항: Flask 앱을 통해 릴레이를 제어하고 싶다면 이 함수를 사용
    예: /control/1/on 또는 /control/1/off
    """
    if group < 1 or group > 8:
        return "잘못된 그룹 번호입니다", 400

    if action not in ['on', 'off']:
        return "잘못된 액션입니다", 400

    try:
        url = f"http://192.168.0.10{group}/relay/{action}"
        response = requests.get(url, timeout=5)
        return f"{group}조 릴레이 {action} 명령 전송 완료: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return f"오류 발생: {str(e)}", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)