from flask import Flask, request, jsonify
import psycopg2
from datetime import datetime
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# PostgreSQL 설정
DB_CONFIG = {
    'host': 'localhost',
    'database': 'weatherdb',
    'user': 'postgres',
    'password': 'smartfarm',
    'port': 5432
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 기존 날씨 데이터 테이블 생성 (온도, 습도 포함)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_data (
            id SERIAL PRIMARY KEY,
            device_id VARCHAR(50),
            timestamp TIMESTAMP,
            rain_detected VARCHAR(20),
            humidity FLOAT,
            temperature FLOAT,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 토양수분 데이터 테이블 생성 (새로 추가)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS soil_moisture_data (
            id SERIAL PRIMARY KEY,
            device_id VARCHAR(50) DEFAULT 'smartfarm_01',
            soil_moisture FLOAT NOT NULL,
            timestamp VARCHAR(50),
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 기존 테이블에 새 컬럼 추가 (이미 있으면 무시)
    try:
        cursor.execute('ALTER TABLE weather_data ADD COLUMN IF NOT EXISTS humidity FLOAT')
        cursor.execute('ALTER TABLE weather_data ADD COLUMN IF NOT EXISTS temperature FLOAT')
        cursor.execute('ALTER TABLE weather_data ALTER COLUMN rain_detected TYPE VARCHAR(20)')
        logging.info("테이블 스키마 업데이트 완료")
    except Exception as e:
        logging.info(f"테이블 업데이트 스킵: {e}")

    conn.commit()
    conn.close()
    logging.info("데이터베이스 초기화 완료")


# 기존 날씨 데이터 엔드포인트
@app.route('/rainfall', methods=['POST'])
def receive_weather_data():
    try:
        data = request.get_json()

        conn = get_db_connection()
        cursor = conn.cursor()

        # 온도, 습도 포함해서 데이터 저장
        cursor.execute('''
            INSERT INTO weather_data (device_id, timestamp, rain_detected, humidity, temperature)
            VALUES (%s, %s, %s, %s, %s)
        ''', (
            data['device_id'],
            data['timestamp'],
            data['rain_detected'],
            data.get('humidity'),  # 없으면 None
            data.get('temperature')  # 없으면 None
        ))

        conn.commit()
        conn.close()

        logging.info(
            f"날씨 데이터 저장: {data['device_id']} - {data['rain_detected']} (온도: {data.get('temperature')}°C, 습도: {data.get('humidity')}%)")
        return jsonify({'status': 'success'}), 200

    except Exception as e:
        logging.error(f"날씨 데이터 저장 오류: {e}")
        return jsonify({'error': str(e)}), 500


# 토양수분 데이터 엔드포인트 (새로 추가)
@app.route('/soil', methods=['POST'])
def receive_soil_moisture():
    try:
        data = request.get_json()

        if not data or 'soil_moisture' not in data:
            return jsonify({'error': 'soil_moisture 데이터가 필요합니다'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 테이블 구조에 맞게 저장
        cursor.execute('''
            INSERT INTO soil_moisture_data (device_id, soil_moisture, timestamp)
            VALUES (%s, %s, %s)
        ''', (
            data.get('device_id', 'smartfarm_01'),
            data['soil_moisture'],
            data.get('timestamp', str(int(datetime.now().timestamp() * 1000)))
        ))

        conn.commit()
        conn.close()

        print(str(int(datetime.now().timestamp() * 1000)))

        logging.info(f"기기 {data.get('device_id', 'smartfarm_01')}: 토양수분 {data['soil_moisture']}% 저장")
        return jsonify({'status': 'success', 'message': '데이터 저장 완료'}), 200

    except Exception as e:
        logging.error(f"토양수분 데이터 저장 오류: {e}")
        return jsonify({'error': str(e)}), 500

# 기존 날씨 데이터 조회
@app.route('/weather_data', methods=['GET'])
def get_weather_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM weather_data ORDER BY received_at DESC LIMIT 10')
        rows = cursor.fetchall()
        conn.close()

        return jsonify([{
            'id': row[0],
            'device_id': row[1],
            'timestamp': str(row[2]),
            'rain_detected': row[3],
            'humidity': row[4],
            'temperature': row[5],
            'received_at': str(row[6])
        } for row in rows])
    except Exception as e:
        logging.error(f"날씨 데이터 조회 오류: {e}")
        return jsonify({'error': str(e)}), 500


# 토양수분 데이터 조회 (새로 추가)
@app.route('/soil_data', methods=['GET'])
def get_soil_moisture_data():
    try:
        # limit 파라미터 받기 (기본값: 20)
        limit = request.args.get('limit', 20, type=int)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM soil_moisture_data 
            ORDER BY received_at DESC 
            LIMIT %s
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()

        return jsonify({
            'count': len(rows),
            'data': [{
                'id': row[0],
                'device_id': row[1],
                'soil_moisture': row[2],
                'timestamp': row[3],
                'received_at': str(row[4])
            } for row in rows]
        })
    except Exception as e:
        logging.error(f"토양수분 데이터 조회 오류: {e}")
        return jsonify({'error': str(e)}), 500


# 최신 토양수분 상태 조회 (새로 추가)
@app.route('/soil_status', methods=['GET'])
def get_latest_soil_status():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT soil_moisture, received_at 
            FROM soil_moisture_data 
            ORDER BY received_at DESC 
            LIMIT 1
        ''')
        row = cursor.fetchone()
        conn.close()

        if row:
            moisture_level = row[0]
            last_updated = str(row[1])

            # 토양수분 상태 판단
            if moisture_level >= 70:
                status = "습함"
                color = "blue"
            elif moisture_level >= 40:
                status = "적당"
                color = "green"
            elif moisture_level >= 20:
                status = "건조"
                color = "orange"
            else:
                status = "매우 건조"
                color = "red"

            return jsonify({
                'soil_moisture': moisture_level,
                'status': status,
                'color': color,
                'last_updated': last_updated,
                'message': f'토양수분: {moisture_level}% ({status})'
            })
        else:
            return jsonify({
                'error': '토양수분 데이터가 없습니다',
                'soil_moisture': None,
                'status': '데이터 없음',
                'color': 'gray'
            }), 404

    except Exception as e:
        logging.error(f"토양수분 상태 조회 오류: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'weather_data': '날씨 데이터 수집',
            'soil_moisture': '토양수분 모니터링'
        }
    }), 200


# 전체 데이터 요약 (새로 추가)
@app.route('/dashboard', methods=['GET'])
def dashboard():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 최신 날씨 데이터
        cursor.execute('''
            SELECT rain_detected, humidity, temperature, received_at 
            FROM weather_data 
            ORDER BY received_at DESC 
            LIMIT 1
        ''')
        weather_row = cursor.fetchone()

        # 최신 토양수분 데이터
        cursor.execute('''
            SELECT soil_moisture, received_at 
            FROM soil_moisture_data 
            ORDER BY received_at DESC 
            LIMIT 1
        ''')
        soil_row = cursor.fetchone()

        conn.close()

        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'weather': {
                'rain_detected': weather_row[0] if weather_row else None,
                'humidity': weather_row[1] if weather_row else None,
                'temperature': weather_row[2] if weather_row else None,
                'last_updated': str(weather_row[3]) if weather_row else None
            } if weather_row else None,
            'soil': {
                'moisture': soil_row[0] if soil_row else None,
                'last_updated': str(soil_row[1]) if soil_row else None
            } if soil_row else None
        }

        return jsonify(dashboard_data)

    except Exception as e:
        logging.error(f"대시보드 데이터 조회 오류: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    init_database()
    logging.info("스마트팜 서버 시작 - 포트 5000")
    app.run(host='0.0.0.0', port=5000)