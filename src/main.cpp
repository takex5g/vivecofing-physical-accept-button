/**
 * M5 Atom S3 - Claude Code Accept Button
 *
 * ボタンを押すとHTTPサーバーにPOSTリクエストを送信し、
 * Claude Codeの確認プロンプトに「y」を送信する
 *
 * PlatformIO用
 */

#include <Arduino.h>
#include <M5AtomS3.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "credentials.h"

// ===== 設定 =====
const char* wifi_ssid = WIFI_SSID;
const char* wifi_password = WIFI_PASSWORD;
const char* server_host = SERVER_HOST;
const int server_port = SERVER_PORT;

// ボタン設定
const int DEBOUNCE_MS = 1000;  // デバウンス時間

// 状態管理
unsigned long lastButtonPress = 0;
bool wifiConnected = false;

// カラー定義
const uint32_t COLOR_READY = 0x00FF00;    // 緑: 準備完了
const uint32_t COLOR_SENDING = 0x0000FF;  // 青: 送信中
const uint32_t COLOR_SUCCESS = 0x00FFFF;  // シアン: 成功
const uint32_t COLOR_ERROR = 0xFF0000;    // 赤: エラー
const uint32_t COLOR_WIFI_CONNECTING = 0xFFFF00; // 黄: WiFi接続中
const uint32_t COLOR_OFF = 0x000000;      // 消灯

// 関数プロトタイプ宣言
void connectWiFi();
void sendAccept();
void showStatus(const char* text, uint32_t color);
void showIP();

void setup() {
    // M5 Atom S3 初期化
    auto cfg = M5.config();
    AtomS3.begin(cfg);

    AtomS3.Display.setTextSize(2);
    AtomS3.Display.setTextColor(WHITE);

    Serial.begin(115200);
    Serial.println("\n=== Claude Code Accept Button ===");

    // WiFi接続
    connectWiFi();
}

void loop() {
    AtomS3.update();

    // WiFi再接続チェック
    if (WiFi.status() != WL_CONNECTED) {
        if (wifiConnected) {
            wifiConnected = false;
            showStatus("WiFi Lost", COLOR_ERROR);
        }
        connectWiFi();
        return;
    }

    // 内蔵ボタン押下検出
    if (AtomS3.BtnA.wasPressed()) {
        Serial.println("Button pressed");
        unsigned long now = millis();
        if (now - lastButtonPress > DEBOUNCE_MS) {
            lastButtonPress = now;
            sendAccept();
        }
    }
}

void connectWiFi() {
    showStatus("Connecting", COLOR_WIFI_CONNECTING);
    Serial.print("Connecting to WiFi: ");
    Serial.println(wifi_ssid);

    WiFi.mode(WIFI_STA);
    WiFi.begin(wifi_ssid, wifi_password);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        wifiConnected = true;
        Serial.println("\nWiFi Connected!");
        Serial.print("IP: ");
        Serial.println(WiFi.localIP());

        showStatus("Ready", COLOR_READY);
        showIP();
    } else {
        Serial.println("\nWiFi Failed!");
        showStatus("WiFi Fail", COLOR_ERROR);
        delay(3000);
    }
}

void sendAccept() {
    showStatus("Sending", COLOR_SENDING);
    Serial.println("Sending accept request...");

    HTTPClient http;
    String url = String("http://") + server_host + ":" + server_port + "/accept";

    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(5000);

    int httpCode = http.POST("");

    if (httpCode > 0) {
        String response = http.getString();
        Serial.print("Response (");
        Serial.print(httpCode);
        Serial.print("): ");
        Serial.println(response);

        if (httpCode == 200) {
            showStatus("Accepted!", COLOR_SUCCESS);
            // 成功フィードバック
            for (int i = 0; i < 2; i++) {
                delay(100);
                AtomS3.Display.fillScreen(BLACK);
                delay(100);
                showStatus("Accepted!", COLOR_SUCCESS);
            }
        } else {
            showStatus("Error", COLOR_ERROR);
        }
    } else {
        Serial.print("HTTP Error: ");
        Serial.println(http.errorToString(httpCode));
        showStatus("Failed", COLOR_ERROR);
    }

    http.end();

    // 1秒後にReadyに戻す
    delay(1000);
    showStatus("Ready", COLOR_READY);
    showIP();
}

void showStatus(const char* text, uint32_t color) {
    AtomS3.Display.fillScreen(BLACK);

    // 背景色インジケーター（画面上部）
    AtomS3.Display.fillRect(0, 0, 128, 20, color);

    // テキスト表示
    AtomS3.Display.setTextSize(2);
    AtomS3.Display.setCursor(10, 50);
    AtomS3.Display.setTextColor(WHITE);
    AtomS3.Display.println(text);
}

void showIP() {
    AtomS3.Display.setTextSize(1);
    AtomS3.Display.setCursor(5, 100);
    AtomS3.Display.print("-> ");
    AtomS3.Display.print(server_host);
}
