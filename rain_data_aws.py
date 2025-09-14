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

    # 테이블 생성 (온도, 습도 포함)
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

    # 기존 테이블에 새 컬럼 추가 (이미 있으면 무시)
    try:
        cursor.execute('ALTER TABLE rainfall_data ADD COLUMN IF NOT EXISTS humidity FLOAT')
        cursor.execute('ALTER TABLE rainfall_data ADD COLUMN IF NOT EXISTS temperature FLOAT')
        cursor.execute('ALTER TABLE rainfall_data ALTER COLUMN rain_detected TYPE VARCHAR(20)')
        logging.info("테이블 스키마 업데이트 완료")
    except Exception as e:
        logging.info(f"테이블 업데이트 스킵: {e}")

    conn.commit()
    conn.close()


@app.route('/rainfall', methods=['POST'])
def receive_data():
    try:
        data = request.get_json()

        conn = get_db_connection()
        cursor = conn.cursor()

        # 온도, 습도 포함해서 데이터 저장
        cursor.execute('''
            INSERT INTO rainfall_data (device_id, timestamp, rain_detected, humidity, temperature)
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
            f"데이터 저장: {data['device_id']} - {data['rain_detected']} (온도: {data.get('temperature')}°C, 습도: {data.get('humidity')}%)")
        return jsonify({'status': 'success'}), 200

    except Exception as e:
        logging.error(f"오류: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/data', methods=['GET'])
def get_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM rainfall_data ORDER BY received_at DESC LIMIT 10')
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


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200


if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=5000)