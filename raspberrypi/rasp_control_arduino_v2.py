#!/usr/bin/env python3
import urllib.request
import json
import time
from datetime import datetime

# 장치 매핑
DEVICES = {
    "192.168.0.101": "smartfarm_01",
    "192.168.0.102": "smartfarm_02",
    "192.168.0.103": "smartfarm_03",
    "192.168.0.104": "smartfarm_04",
    "192.168.0.106": "smartfarm_06",
    "192.168.0.107": "smartfarm_07",
    "192.168.0.108": "smartfarm_08",
    "192.168.0.109": "smartfarm_09",

}

API_URL = "http://34.229.121.126:5000/api/soil"
THRESHOLD = 40  # 토양습도 임계값


def log(msg):
    print(f"{datetime.now().strftime('%H:%M:%S')} - {msg}")


def get_soil_moisture(farm_id):
    try:
        response = urllib.request.urlopen(f"{API_URL}/{farm_id}", timeout=5)
        data = json.loads(response.read().decode('utf-8'))
        return data.get('soil_moisture')
    except:
        return None


def relay_control(ip, cmd):
    try:
        urllib.request.urlopen(f"http://{ip}/relay/{cmd}", timeout=5)
        return True
    except:
        return False


def main():
    log("🚀 스마트팜 자동관수 시작")

    # 네트워크 대기
    time.sleep(60)

    # 토양습도 체크 및 릴레이 제어
    active_devices = []

    for ip, farm_id in DEVICES.items():
        moisture = get_soil_moisture(farm_id)
        log(f"{farm_id}: {moisture}%")

        if moisture and moisture <= THRESHOLD:
            if relay_control(ip, "on"):
                active_devices.append(ip)
                log(f"💧 {farm_id} 물주기 시작")

    if active_devices:
        log("⏰ 3분 대기...")
        time.sleep(180)

        for ip in active_devices:
            relay_control(ip, "off")
            log("🔄 물주기 종료")

    log("✅ 완료")


if __name__ == "__main__":
    main()