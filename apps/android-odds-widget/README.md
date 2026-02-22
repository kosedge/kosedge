# Kos Edge Odds — Android widget (Fire tablet)

Minimal Android app with a **CBB odds widget** (ticker style, Kos colors). Updates **hourly from 6:00 AM to 10:00 PM** only (no overnight API calls).

## Build on Mac

1. **Install Android Studio** (runs on macOS): https://developer.android.com/studio
2. **Open the project**: File → Open → select `apps/android-odds-widget`.
3. **API URL**: Pre-set to `https://www.kosedge.com/api/edge-board/ncaam/today` in `OddsWorker.kt`. Edit if you need a different base URL.
4. **Build**: Build → Build Bundle(s) / APK(s) → Build APK(s).
5. **Install on Fire tablet**: Copy the APK from `app/build/outputs/apk/debug/` to the tablet (USB or cloud) and open it to install. Enable “Install from unknown sources” if prompted.

## Widget behavior

- **Data**: Reads from your existing `/api/edge-board/ncaam/today` JSON (`rows` with `game`, `market`, `open`, `best`).
- **Schedule**: WorkManager runs every hour; the worker only fetches when the device hour is 6–22 (6 AM–10 PM).
- **UI**: Ticker-style list: game name, Open line/O/U, Best line/O/U (Kos black/gold theme).

## Add the widget

On the Fire tablet, long-press home screen → Widgets → find **CBB Odds** under Kos Edge Odds → drag to home screen.

## Optional: launcher icon

To use a custom launcher icon: in Android Studio, File → New → Image Asset, then replace `app/src/main/res/drawable/ic_launcher.xml` or add mipmap icons and point the manifest back to `@mipmap/ic_launcher`.
