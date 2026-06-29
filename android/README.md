# 台股交易帳本 - Android APP

## 專案結構

```
android/
├── app/
│   ├── build.gradle              # Gradle 設定 (Chaquopy + Flask)
│   ├── src/main/
│   │   ├── AndroidManifest.xml   # APP 設定
│   │   ├── java/com/stocktracker/app/
│   │   │   └── MainActivity.kt   # 主 Activity (WebView + Flask)
│   │   ├── python/
│   │   │   ├── flask_server.py   # Flask 啟動/停止
│   │   │   └── setup_app.py      # 初次設定
│   │   └── res/
│   │       ├── layout/activity_main.xml
│   │       └── values/
│   └── proguard-rules.pro
├── build.gradle
├── settings.gradle
└── gradle.properties
```

## 環境需求

- Android Studio Hedgehog (2023.1.1) 以上
- JDK 17
- Android SDK 34 (API 34)
- Python 3.11 (Chaquopy 會使用)
- NDK (任意版本，Chaquopy 需要)

## 建置步驟

### 1. 安裝 Android Studio

從 https://developer.android.com/studio 下載安裝。

### 2. 安裝必要 SDK 元件

開啟 Android Studio → Tools → SDK Manager：
- Android SDK Platform 34
- Android SDK Build-Tools 34.0.0
- NDK (Side by side)
- CMake

### 3. 安裝 Chaquopy 外掛

Android Studio → File → Settings → Plugins → 搜尋 "Chaquopy" → 安裝

### 4. 複製程式碼到 Android 專案

```bash
# 將 stock-tracker 原始碼複製到 Android 專案
cp -r ../stock-tracker app/src/main/assets/stock-tracker-source/
```

或在 Android Studio 中手動複製 `stock-tracker/` 資料夾到 `app/src/main/assets/stock-tracker-source/`。

### 5. 開啟專案

File → Open → 選擇 `android/` 資料夾

### 6. 建置 APK

Build → Build Bundle(s) / APK(s) → Build APK(s)

APK 會產出在 `app/build/outputs/apk/debug/app-debug.apk`

### 7. 安裝到手機

```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

或直接從手機設定 → 安全性 → 允許未知來源 → 安裝 APK。

## 運作原理

1. APP 啟動時透過 **Chaquopy** 嵌入 Python 3.11
2. Python 啟動 Flask 本機伺服器 (`127.0.0.1:5000`)
3. **WebView** 載入 `http://127.0.0.1:5000`
4. 所有 API 呼叫都在本機完成，不需要網路連線（股價抓取除外）

## 注意事項

- 首次啟動會複製程式碼到 APP 內部儲存空間
- 資料存放在 `/data/data/com.stocktracker.app/files/stock-tracker/data/`
- 清除 APP 資料會刪除所有持倉記錄
- 股價抓取需要網路連線
