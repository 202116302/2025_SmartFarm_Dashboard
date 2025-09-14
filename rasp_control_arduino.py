#!/usr/bin/env python3
import urllib.request
import time
from datetime import datetime

# 아두이노 IP 주소들
devices = [
    "192.168.0.101",
    "192.168.0.102",
    "192.168.0.103",
    "192.168.0.104",
    "192.168.0.106",
    "192.168.0.107",
    "192.168.0.108",
    "192.168.0.109", 
]

print(f"🌅 {datetime.now()} - 시작")

# ON 신호
print("📡 릴레이 ON...")
for ip in devices:
    try:
        urllib.request.urlopen(f"http://{ip}/relay/on", timeout=20)
        print(f"✅ {ip} ON 성공")
    except:
        print(f"❌ {ip} ON 실패")

print("⏳ 3분 대기...")
time.sleep(180)  # 3분

# OFF 신호  
print("📡 릴레이 OFF...")
for ip in devices:
    try:
        urllib.request.urlopen(f"http://{ip}/relay/off", timeout=20)
        print(f"✅ {ip} OFF 성공")
    except:
        print(f"❌ {ip} OFF 실패")

print(f"🏁 {datetime.now()} - 완료!")
