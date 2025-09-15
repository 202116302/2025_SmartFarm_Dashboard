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
        timestamp = str(datetime.now().isoformat())

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
            timestamp
        ))

        conn.commit()
        conn.close()

        print(timestamp)

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


# ========== 날씨 센서 API (단일 라즈베리파이) ==========

@app.route('/api/weather', methods=['GET'])
def get_weather():
    """최신 날씨 데이터 (온도, 습도, 강우) 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT device_id, rain_detected, humidity, temperature, received_at 
            FROM weather_data 
            ORDER BY received_at DESC 
            LIMIT 1
        ''')
        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({
                'device_id': row[0],
                'rain_status': row[1],
                'humidity': row[2],
                'temperature': row[3],
                'last_updated': str(row[4])
            })
        return jsonify({'message': '날씨 데이터가 없습니다'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/weather/rain', methods=['GET'])
def get_rain_only():
    """강우 상태만 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT rain_detected, received_at 
            FROM weather_data 
            ORDER BY received_at DESC 
            LIMIT 1
        ''')
        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({
                'rain_status': row[0],
                'last_updated': str(row[1])
            })
        return jsonify({'message': '강우 데이터가 없습니다'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== 토양수분 센서 API (다중 센서) ==========

@app.route('/api/soil/all', methods=['GET'])
def get_all_soil_sensors():
    """모든 토양수분 센서의 최신 데이터"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT device_id, soil_moisture, received_at,
                   ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY received_at DESC) as rn
            FROM soil_moisture_data
        ''')

        # 각 디바이스별 최신 데이터만 필터링
        all_rows = cursor.fetchall()
        latest_data = [row for row in all_rows if row[3] == 1]  # rn = 1인 것만

        conn.close()

        if latest_data:
            sensors = []
            for row in latest_data:
                sensors.append({
                    'device_id': row[0],
                    'soil_moisture': row[1],
                    'last_updated': str(row[2])
                })

            return jsonify({
                'total_sensors': len(sensors),
                'sensors': sensors
            })

        return jsonify({'message': '토양수분 데이터가 없습니다'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/soil/<device_id>', methods=['GET'])
def get_soil_sensor(device_id):
    """특정 토양수분 센서 데이터"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT soil_moisture, received_at 
            FROM soil_moisture_data 
            WHERE device_id = %s
            ORDER BY received_at DESC 
            LIMIT 1
        ''', (device_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({
                'device_id': device_id,
                'soil_moisture': row[0],
                'last_updated': str(row[1])
            })
        return jsonify({'message': f'{device_id} 토양수분 데이터가 없습니다'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/soil/list', methods=['GET'])
def get_soil_device_list():
    """토양수분 센서 디바이스 목록"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT device_id, COUNT(*) as data_count, MAX(received_at) as last_update
            FROM soil_moisture_data 
            GROUP BY device_id
            ORDER BY last_update DESC
        ''')
        rows = cursor.fetchall()
        conn.close()

        if rows:
            devices = []
            for row in rows:
                devices.append({
                    'device_id': row[0],
                    'data_count': row[1],
                    'last_update': str(row[2])
                })

            return jsonify({
                'total_devices': len(devices),
                'devices': devices
            })

        return jsonify({'message': '토양수분 센서가 없습니다'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== 통합 조회 API ==========

@app.route('/api/summary', methods=['GET'])
def get_farm_summary():
    """전체 농장 센서 요약"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 최신 날씨 데이터
        cursor.execute('''
            SELECT device_id, rain_detected, humidity, temperature, received_at 
            FROM weather_data 
            ORDER BY received_at DESC 
            LIMIT 1
        ''')
        weather_row = cursor.fetchone()

        # 모든 토양수분 센서의 최신 데이터
        cursor.execute('''
            SELECT device_id, soil_moisture, received_at,
                   ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY received_at DESC) as rn
            FROM soil_moisture_data
        ''')
        all_soil_rows = cursor.fetchall()
        soil_sensors = [row for row in all_soil_rows if row[3] == 1]

        conn.close()

        result = {}

        # 날씨 데이터
        if weather_row:
            result['weather'] = {
                'device_id': weather_row[0],
                'rain_status': weather_row[1],
                'humidity': weather_row[2],
                'temperature': weather_row[3],
                'last_updated': str(weather_row[4])
            }

        # 토양수분 데이터
        if soil_sensors:
            result['soil_sensors'] = []
            for row in soil_sensors:
                result['soil_sensors'].append({
                    'device_id': row[0],
                    'soil_moisture': row[1],
                    'last_updated': str(row[2])
                })

        if result:
            return jsonify(result)
        return jsonify({'message': '데이터가 없습니다'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== API 목록 ==========

@app.route('/api', methods=['GET'])
def api_list():
    return jsonify({
        'message': '스마트팜 센서 API',
        'weather_apis': {
            '/api/weather': '전체 날씨 데이터 (온도, 습도, 강우)',
            '/api/weather/rain': '강우 상태만'
        },
        'soil_apis': {
            '/api/soil/all': '모든 토양수분 센서 데이터',
            '/api/soil/<device_id>': '특정 토양수분 센서',
            '/api/soil/list': '토양수분 센서 목록'
        },
        'summary_apis': {
            '/api/summary': '전체 농장 센서 요약',
            '/health': '서버 상태'
        }
    })


if __name__ == '__main__':
    init_database()
    logging.info("스마트팜 서버 시작 - 포트 5000")
    app.run(host='0.0.0.0', port=5000)