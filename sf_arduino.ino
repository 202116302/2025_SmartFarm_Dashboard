#include <SoftwareSerial.h>

SoftwareSerial esp01(2, 3);

// 네트워크 설정 (여기서 변경하세요!)
const char* WIFI_SSID = "SmartFarm_GP";     // WiFi 이름
const char* WIFI_PASS = "smartfarm!";       // WiFi 비밀번호  
const char* STATIC_IP = "192.168.0.102";    // 고정 IP 주소
const char* GATEWAY = "192.168.0.1";        // 게이트웨이 (라우터 IP)
const char* SUBNET = "255.255.255.0";       // 서브넷 마스크
const char* DEVICE_ID = "smartfarm_02";  // 기기마다 다르게

// 핀 설정
const int relayPin = 7;
const int soilSensorPin = A0;

// 상태 변수
bool relayState = false;
int soilMoisture = 0;

// 타이머 변수 (AWS 전송용)
unsigned long lastDataSend = 0;
const unsigned long sendInterval = 600000;  // 10분마다 AWS 전송

void setup() {
  Serial.begin(9600);
  esp01.begin(9600);
  
  pinMode(relayPin, OUTPUT);
  pinMode(soilSensorPin, INPUT);
  digitalWrite(relayPin, LOW);
  
  Serial.println(F("=== 스마트팜 시작 ==="));
  delay(2000);
  
  setupWiFi();
}

void setupWiFi() {
  Serial.println(F("1. AT 테스트"));
  esp01.println(F("AT"));
  delay(1000);
  readResponse();
  
  Serial.println(F("2. WiFi 모드"));
  esp01.println(F("AT+CWMODE=1"));
  delay(1000);
  readResponse();
  
  Serial.println(F("3. WiFi 연결"));
  esp01.print(F("AT+CWJAP=\""));
  esp01.print(WIFI_SSID);
  esp01.print(F("\",\""));
  esp01.print(WIFI_PASS);
  esp01.println(F("\""));
  delay(8000);
  readResponse();
  
  Serial.println(F("4. 고정 IP 설정"));
  esp01.print(F("AT+CIPSTA=\""));
  esp01.print(STATIC_IP);
  esp01.print(F("\",\""));
  esp01.print(GATEWAY);
  esp01.print(F("\",\""));
  esp01.print(SUBNET);
  esp01.println(F("\""));
  delay(3000);
  readResponse();
  
  Serial.println(F("5. IP 확인"));
  esp01.println(F("AT+CIFSR"));
  delay(3000);
  
  // IP 주소 파싱해서 표시
  String response = "";
  while (esp01.available()) {
    char c = esp01.read();
    response += c;
    Serial.write(c);
    delay(1);
  }
  
  // 고정 IP 확인 메시지
  if (response.indexOf(STATIC_IP) != -1) {
    Serial.println(F("\n🌐 === 고정 IP 설정 성공! ==="));
    Serial.print(F("📍 IP 주소: "));
    Serial.println(STATIC_IP);
    Serial.print(F("🔗 웹 접속: http://"));
    Serial.print(STATIC_IP);
    Serial.println(F("/"));
    Serial.print(F("💧 급수 ON: http://"));
    Serial.print(STATIC_IP);
    Serial.println(F("/relay/on"));
    Serial.print(F("🛑 급수 OFF: http://"));
    Serial.print(STATIC_IP);
    Serial.println(F("/relay/off"));
    Serial.print(F("📊 상태: http://"));
    Serial.print(STATIC_IP);
    Serial.println(F("/status"));
  } else {
    Serial.println(F("\n⚠️ 고정 IP 설정 실패 - DHCP 사용"));
  }
  
  Serial.println(F("6. 웹서버 시작"));
  esp01.println(F("AT+CIPMUX=1"));
  delay(1000);
  readResponse();
  
  esp01.println(F("AT+CIPSERVER=1,80"));
  delay(1000);
  readResponse();
  
  Serial.println(F("=== 설정 완료 ==="));
}

void loop() {
  unsigned long currentTime = millis();
  
  // AWS 전송 (30초마다)
  if (currentTime - lastDataSend >= sendInterval) {
    sendToAWS();
    lastDataSend = currentTime;
  }
  
  // 수동 테스트
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == 's') {
      sendToAWS();
    } else if (cmd == '1') {
      digitalWrite(relayPin, HIGH);
      relayState = true;
      Serial.println(F("릴레이 ON"));
    } else if (cmd == '0') {
      digitalWrite(relayPin, LOW);
      relayState = false;
      Serial.println(F("릴레이 OFF"));
    }
  }
  
  // 웹 요청 처리
  handleWeb();
  
  delay(100);
}

// AWS 전송 (완전 수정 버전)
void sendToAWS() {
  // 토양수분 읽기
  int raw = analogRead(soilSensorPin);
  soilMoisture = map(raw, 800, 300, 0, 100);
  soilMoisture = constrain(soilMoisture, 0, 100);
  
  Serial.print(F("토양수분: "));
  Serial.print(soilMoisture);
  Serial.println(F("%"));
  
  Serial.println(F("AWS 전송중..."));
  
  // TCP 연결
  esp01.println(F("AT+CIPSTART=3,\"TCP\",\"34.229.121.126\",5000"));
  delay(5000);
  
  if (waitForOK()) {
    Serial.println(F("TCP 연결 성공"));
    
    // JSON 생성 - 테이블 구조에 맞게
    char json[80];
    sprintf(json, "{\"device_id\":\"%s\",\"soil_moisture\":\"%d\"}", 
            DEVICE_ID, soilMoisture);
    
    int jsonLength = strlen(json);
    Serial.print(F("JSON: "));
    Serial.println(json);
    Serial.print(F("JSON 길이: "));
    Serial.println(jsonLength);
    
    // HTTP 요청을 문자열로 미리 구성
    String httpHeader = "POST /soil HTTP/1.1\r\n";
    httpHeader += "Host: 34.229.121.126\r\n";
    httpHeader += "Content-Type: application/json\r\n";
    httpHeader += "Content-Length: " + String(jsonLength) + "\r\n";
    httpHeader += "Connection: close\r\n\r\n";
    
    int totalLength = httpHeader.length() + jsonLength;
    
    Serial.print(F("헤더 길이: "));
    Serial.println(httpHeader.length());
    Serial.print(F("전체 길이: "));
    Serial.println(totalLength);
    
    // AT+CIPSEND 명령
    esp01.print(F("AT+CIPSEND=3,"));
    esp01.println(totalLength);
    delay(2000);
    
    // ">" 프롬프트 대기
    if (esp01.find(">")) {
      Serial.println(F("전송 시작"));
      
      // 헤더 전송
      esp01.print(httpHeader);
      // JSON 데이터 전송  
      esp01.print(json);
      
      Serial.println(F("전송 완료, 응답 대기중..."));
      delay(8000);
      
      // 응답 읽기
      Serial.println(F("=== 서버 응답 ==="));
      while (esp01.available()) {
        Serial.write(esp01.read());
      }
      Serial.println(F("\n=================="));
      
    } else {
      Serial.println(F("'>' 프롬프트 못받음"));
      
      // ESP-01 상태 확인
      while (esp01.available()) {
        Serial.write(esp01.read());
      }
    }
  } else {
    Serial.println(F("TCP 연결 실패"));
  }
  
  // 연결 종료
  esp01.println(F("AT+CIPCLOSE=3"));
  delay(1000);
}

// 웹 요청 처리 (간단 버전)
void handleWeb() {
  if (esp01.available()) {
    delay(100); // 요청 완전히 받기
    
    bool isRelayOn = false;
    bool isRelayOff = false;
    bool isStatus = false;
    
    // 요청 파싱
    while (esp01.available()) {
      String line = esp01.readStringUntil('\n');
      if (line.indexOf("GET /relay/on") != -1) isRelayOn = true;
      else if (line.indexOf("GET /relay/off") != -1) isRelayOff = true;
      else if (line.indexOf("GET /status") != -1) isStatus = true;
    }
    
    // 릴레이 제어
    if (isRelayOn) {
      digitalWrite(relayPin, HIGH);
      relayState = true;
      Serial.println(F("웹: 릴레이 ON"));
      sendSimpleResponse("ON");
    }
    else if (isRelayOff) {
      digitalWrite(relayPin, LOW);
      relayState = false;
      Serial.println(F("웹: 릴레이 OFF"));
      sendSimpleResponse("OFF");
    }
    else if (isStatus) {
      int raw = analogRead(soilSensorPin);
      int moisture = map(raw, 800, 300, 0, 100);
      moisture = constrain(moisture, 0, 100);
      
      char status[50];
      sprintf(status, "Soil:%d%%, Relay:%s", moisture, relayState ? "ON" : "OFF");
      sendSimpleResponse(status);
    }
  }
}

// 간단한 응답 전송
void sendSimpleResponse(const char* message) {
  int msgLen = strlen(message);
  int totalLen = 45 + msgLen; // 간단한 헤더 + 메시지
  
  char cmd[20];
  sprintf(cmd, "AT+CIPSEND=0,%d", totalLen);
  esp01.println(cmd);
  delay(100);
  
  if (esp01.find(">")) {
    esp01.print(F("HTTP/1.1 200 OK\r\n"));
    esp01.print(F("Connection: close\r\n\r\n"));
    esp01.print(message);
  }
  
  delay(100);
  esp01.println(F("AT+CIPCLOSE=0"));
}

// OK 응답 대기
bool waitForOK() {
  unsigned long start = millis();
  while (millis() - start < 8000) {
    if (esp01.find("OK")) return true;
  }
  return false;
}

// 응답 읽기
void readResponse() {
  delay(100);
  while (esp01.available()) {
    Serial.write(esp01.read());
    delay(1);
  }
}