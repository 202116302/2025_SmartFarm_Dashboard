import requests
import json
from gpiozero import DigitalInputDevice
from datetime import datetime
import time
import logging

logging.basicConfig(level=logging.INFO)

# 설정
RAIN_SENSOR_PIN = 17
EC2_ENDPOINT = "http://34.229.121.126:5000/rainfall"
DEVICE_ID = "raspberry_rain"

rain_sensor = DigitalInputDevice(RAIN_SENSOR_PIN)


def send_data():
    if not rain_sensor.is_active:
        is_raining = "rain"
    else:
        is_raining = "no_rain"
    data = {
        "device_id": DEVICE_ID,
        "timestamp": datetime.now().isoformat(),
        "rain_detected": is_raining
    }

    try:
        response = requests.post(EC2_ENDPOINT, json=data, timeout=10)
        if response.status_code == 200:
            logging.info(f"전송 성공: {'비' if is_raining else '맑음'}")
        else:
            logging.error(f"전송 실패: {response.status_code}")
    except Exception as e:
        logging.error(f"오류: {e}")


if __name__ == "__main__":
    while True:
        send_data()
        time.sleep(300)  # 5분 대기