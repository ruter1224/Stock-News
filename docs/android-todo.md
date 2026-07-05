# Stock Tracker 手機版 (Android APK) 未完成事項

> 建立日期：2026-06-29  
> 最後更新：2026-07-05  
> 狀態：進行中

---

## 專案概況

- **架構**：Chaquopy (Python 3.11) + Flask + WebView
- **APK 路徑**：`android/app/build/outputs/apk/debug/app-debug.apk`
- **目前版本**：Debug v1.0 (54.86 MB)
- **GitHub**：https://github.com/ruter1224/Stock-News (branch: `feature/news`)

---

## 🔴 高優先（影響核心使用）

### 1. Release APK 簽名
- [ ] 建立 keystore (`keytool -genkey -v ...`)
- [ ] 在 `build.gradle` 設定 `signingConfigs`
- [ ] 設定 `buildTypes.release` 使用簽名
- [ ] 測試 Release APK 安裝與執行
- [ ] 確認 Release 版 APK 大小與效能

### 2. App 圖示 (Icon)
- [ ] 設計 App 圖示 (建議 1024x1024 原始檔)
- [ ] 產生各尺寸：mipmap-mdpi ~ xxxhdpi
- [ ] 替換 `res/mipmap-*/ic_launcher.png`
- [ ] 設定 adaptive icon (Android 8.0+)

### 3. 初始資料匯入
- [ ] 手機首次開啟無持股資料
- [ ] 提供 CSV 匯入引導流程
- [ ] 或提供「快速新增初始持倉」的 onboarding
- [ ] 考慮：從電腦版匯出 → 手機版匯入的流程

### 4. WebView 錯誤處理
- [x] Flask 啟動失敗時顯示 fallback 頁面（目前可能白屏）
- [x] WebView 載入逾時處理
- [x] 加入「重試」按鈕
- [x] 顯示具體錯誤訊息供除錯

---

## 🟡 中優先（改善穩定性與體驗）

### 5. 檔案同步機制
- [ ] `stock-tracker/` 和 `android/app/src/main/python/` 的 Python 檔案重複
- [ ] `stock-tracker/web/` 和 `android/app/src/main/assets/web/` 的前端檔案重複
- [ ] 修改時需手動同步兩處，容易遺漏
- [ ] 方案 A：建立同步腳本 (copy script)
- [ ] 方案 B：改用 symbolic link 或 shared module
- [ ] 方案 C：Android 直接引用 stock-tracker 目錄

### 6. 背景執行策略
- [ ] App 切到背景時 Flask 是否繼續執行？
- [ ] `onPause` / `onResume` 生命周期處理
- [ ] 考慮：背景時暫停 Flask 以節省電量？
- [ ] 考慮：回到前台時自動重新載入 WebView

### 7. 離線模式
- [ ] 無網路時 graceful degradation
- [ ] 顯示最後快取的股價（標記為「離線模式」）
- [ ] 禁止「更新股價」按鈕並提示
- [ ] 本地操作（新增交易等）不受影響

### 8. ProGuard / R8 規則
- [ ] Release build 需要 code shrinking 設定
- [ ] 建立 `proguard-rules.pro`
- [ ] 保留 Chaquopy Python bridge 相關 class
- [ ] 測試 Release build 不會 crash

### 9. ANDROID_HOME 環境變數
- [ ] 目前 build 需手動設定 `$env:ANDROID_HOME = "C:\Android"`
- [ ] 建議加入系統環境變數或 `local.properties`（已在 .gitignore）
- [ ] 記錄 build 指令到 README

---

## 🟢 低優先（錦上添花）

### 10. Splash Screen
- [ ] 啟動畫面（顯示 App 名稱 + 載入動畫）
- [ ] 取代目前的白色 loading 畫面
- [ ] 可考慮使用 Android SplashScreen API

### 11. 版本管理
- [ ] `versionCode` / `versionName` 目前 hardcoded
- [ ] 考慮自動版本號（git commit count 或 date）
- [ ] App 內顯示版本資訊

### 12. Crash 回報
- [ ] 當機時收集 log
- [ ] 可選：Firebase Crashlytics 整合
- [ ] 或本地 crash log 檔案供匯出

### 13. 效能最佳化
- [ ] 減少 APK 大小（目前 ~55MB，主要是 Python runtime + 依賴）
- [ ] 考慮只保留 arm64-v8a（移除 armeabi-v7a, x86_64）
- [ ] WebView 預載策略

### 14. UI/UX 改善
- [ ] 手機版 RWD 最佳化（目前直接套用桌面版 CSS）
- [ ] 觸控操作最佳化（按鈕大小、間距）
- [ ] 深色模式支援
- [ ] 下拉重新整理手勢

---

## ✅ 已完成

| 日期 | 項目 | 說明 |
|------|------|------|
| 2026-06-29 | Android 專案結構 | Chaquopy + Flask + WebView 架構完成 |
| 2026-06-29 | Debug APK 打包 | 成功 build app-debug.apk |
| 2026-06-29 | 網路最佳化 | 移除啟動時自動抓股價、延長快取 TTL 至 30 分鐘 |
| 2026-06-29 | .gitignore 設定 | 排除 build 產出、local.properties |
| 2026-06-29 | Chart.js 圖表 | 回測頁面圖表功能 |
| 2026-07-05 | WebView 錯誤處理 | 新增錯誤畫面與重試按鈕，改善白屏問題 |

---

## 已知問題

| 問題 | 說明 | 狀態 |
|------|------|------|
| Debug APK 網路延遲 | 開啟 App 會自動抓股價造成延遲 | ✅ 已修復 |
| 快取 TTL 過短 | 5 分鐘太短，頻繁請求外部 API | ✅ 已修復 (→30分鐘) |
| refreshPrices 清除快取 | 手動更新時會全部清除再重抓 | ✅ 已修復 |
| Python 3.11 套件相容性 | Chaquopy 警告可能套件較少 | ⚠️ 待觀察 |
| 兩處程式碼重複 | stock-tracker/ 與 android/ 需手動同步 | ⏳ 待處理 |

---

## Build 指令備忘

```powershell
# Debug build
$env:ANDROID_HOME = "C:\Android"
cd android
.\gradlew.bat assembleDebug

# APK 位置
android\app\build\outputs\apk\debug\app-debug.apk

# 清理重建
.\gradlew.bat clean assembleDebug
```
