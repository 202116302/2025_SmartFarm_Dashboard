from flask import Flask, render_template_string

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
            align-items: center;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
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
        .btn:disabled {
            background-color: #bdc3c7;
            cursor: not-allowed;
        }
        .status {
            margin-left: 20px;
            font-size: 14px;
            color: #7f8c8d;
        }
        .result {
            margin-left: 20px;
            font-size: 14px;
            padding: 5px 10px;
            border-radius: 3px;
            display: none;
        }
        .result.success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .result.error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .loading {
            display: none;
            margin-left: 10px;
            font-size: 14px;
            color: #6c757d;
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
                <button class="btn btn-on" onclick="controlRelay({{ i }}, 'on', this)">
                    💧 물주기 ON
                </button>
                <button class="btn btn-off" onclick="controlRelay({{ i }}, 'off', this)">
                    ⏹️ 물주기 OFF
                </button>
                <span class="loading" id="loading-{{ i }}">⏳ 전송중...</span>
                <span class="status">IP: 192.168.0.10{{ i }}</span>
                <div class="result" id="result-{{ i }}"></div>
            </div>
        </div>
        {% endfor %}

        <div style="text-align: center; margin-top: 30px; color: #95a5a6;">
            <p>💡 버튼을 클릭하면 해당 장치로 직접 명령이 전송됩니다</p>
        </div>
    </div>

    <script>
        function controlRelay(group, action, button) {
            const loadingEl = document.getElementById('loading-' + group);
            const resultEl = document.getElementById('result-' + group);

            // 로딩 표시
            loadingEl.style.display = 'inline';
            resultEl.style.display = 'none';
            button.disabled = true;

            // 직접 아두이노로 요청
            const arduinoUrl = `http://192.168.0.10${group}/relay/${action}`;
            console.log('요청 URL:', arduinoUrl);

            fetch(arduinoUrl, {
                method: 'GET',
                mode: 'no-cors'
            })
                .then(() => {
                    loadingEl.style.display = 'none';
                    resultEl.textContent = `${group}조 릴레이 ${action.toUpperCase()} 명령 전송완료!`;
                    resultEl.className = 'result success';
                    resultEl.style.display = 'inline-block';
                    button.disabled = false;

                    setTimeout(() => {
                        resultEl.style.display = 'none';
                    }, 3000);
                })
                .catch(error => {
                    loadingEl.style.display = 'none';
                    resultEl.textContent = `오류: 아두이노 연결 실패 (${group}조)`;
                    resultEl.className = 'result error';
                    resultEl.style.display = 'inline-block';
                    button.disabled = false;

                    setTimeout(() => {
                        resultEl.style.display = 'none';
                    }, 5000);
                });
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(template)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=True)