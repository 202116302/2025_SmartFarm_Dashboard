from flask import Flask, request, jsonify
import psycopg2
from datetime import datetime
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# PostgreSQL 설정
DB_CONFIG = {
    'host': 'localhost',
    'database': 'raindb',
    'user': 'postgres',
    'password': 'smartfarm',
    'port': 5432
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rainfall_data (
            id SERIAL PRIMARY KEY,
            device_id VARCHAR(50),
            timestamp TIMESTAMP,
            rain_detected BOOLEAN,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


@app.route('/rainfall', methods=['POST'])
def receive_data():
    try:
        data = request.get_json()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO rainfall_data (device_id, timestamp, rain_detected)
            VALUES (%s, %s, %s)
        ''', (data['device_id'], data['timestamp'], data['rain_detected']))

        conn.commit()
        conn.close()

        logging.info(f"데이터 저장: {data['device_id']} - {'비' if data['rain_detected'] else '맑음'}")
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
        'id': row[0], 'device_id': row[1], 'timestamp': str(row[2]),
        'rain_detected': row[3], 'received_at': str(row[4])
    } for row in rows])


if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=5000)