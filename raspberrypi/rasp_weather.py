import requests
import json
from gpiozero import DigitalInputDevice
from datetime import datetime
import board
import time
import logging
import adafruit_dht

logging.basicConfig(level=logging.INFO)

# 설정
RAIN_SENSOR_PIN = 17
EC2_ENDPOINT = "http://34.229.121.126:5000/rainfall"
DEVICE_ID = "raspberry_sf"

# 센서 초기화
rain_sensor = DigitalInputDevice(RAIN_SENSOR_PIN)
dhtDevice = adafruit_dht.DHT11(board.D2) # 센서 타입


def read_temp_humidity():
    """온습도 센서 값 읽기"""
    try:
        temperature = dhtDevice.temperature
        humidity = dhtDevice.humidity
        if humidity is not None and temperature is not None:
            return round(humidity, 1), round(temperature, 1)
        else:
            logging.warning("온습도 센서 읽기 실패")
            return None, None
    except Exception as e:
        logging.error(f"온습도 센서 오류: {e}")
        return None, None

def send_data():
    # 강우 센서 읽기
    if not rain_sensor.is_active:
        is_raining = "rain"
        rain_status = "비"
    else:
        is_raining = "no_rain"
        rain_status = "맑음"
    
    # 온습도 센서 읽기
    humidity, temperature = read_temp_humidity()
    
    # 전송할 데이터 구성
    data = {
        "device_id": DEVICE_ID,
        "timestamp": datetime.now().isoformat(),
        "rain_detected": is_raining,
        "humidity": humidity,
        "temperature": temperature
    }
    
    try:
        response = requests.post(EC2_ENDPOINT, json=data, timeout=30)
        if response.status_code == 200:
            logging.info(f"전송 성공: {rain_status}, 온도: {temperature}°C, 습도: {humidity}%, {datetime.now().isoformat()}")
        else:
            logging.error(f"전송 실패: {response.status_code}")
            logging.error(f"응답 내용: {response.text}")
    except Exception as e:
        logging.error(f"오류: {e}")

if __name__ == "__main__":
    send_data()
