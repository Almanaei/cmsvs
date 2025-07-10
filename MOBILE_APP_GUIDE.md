# CMSVS Mobile App Guide

## Overview

This guide explains how to build and deploy the CMSVS mobile hybrid app using Capacitor. The mobile app maintains your existing web functionality while adding native mobile features.

## Architecture

- **Backend**: FastAPI (unchanged) - serves both web and mobile API
- **Frontend**: Tailwind CSS + HTML/JS (adapted for mobile)
- **Mobile Framework**: Capacitor (converts web app to native mobile app)
- **Platforms**: Android and iOS

## Features Added

### ✅ Completed Features

1. **Native Mobile App Structure**
   - Android project setup
   - iOS project setup (ready)
   - App icons and splash screens
   - Native navigation

2. **Mobile-Specific UI**
   - Mobile-optimized index page
   - Touch-friendly interface
   - Pull-to-refresh functionality
   - Safe area handling for notched devices

3. **Offline Capabilities**
   - Service Worker for offline caching
   - Offline data synchronization
   - Background sync when connection restored

4. **Push Notifications**
   - Push notification setup
   - Token registration with backend
   - Notification handling and display

5. **Native Device Features**
   - Camera access for photo capture
   - File system access
   - Haptic feedback
   - Status bar customization
   - Keyboard handling

6. **Mobile API Endpoints**
   - `/api/mobile/register-token` - Register push tokens
   - `/api/mobile/config` - Get app configuration
   - `/api/mobile/sync-offline-data` - Sync offline actions
   - `/api/mobile/health` - Health check
   - `/api/mobile/feedback` - Submit feedback

## Project Structure

```
cmsvs/
├── android/                 # Android native project
├── ios/                     # iOS native project (when added)
├── www/                     # Mobile web assets
│   ├── index.html          # Mobile app entry point
│   ├── sw.js               # Service worker
│   └── static/             # CSS, JS, images
├── app/routes/mobile.py     # Mobile API endpoints
├── scripts/build-mobile.js  # Mobile build script
└── capacitor.config.json    # Capacitor configuration
```

## Development Workflow

### 1. Making Changes to Mobile App

```bash
# 1. Make changes to your web app (app/templates, app/static, etc.)

# 2. Build mobile assets
npm run mobile:build

# 3. Sync with native projects
npx cap sync android

# 4. Test in browser (optional)
npx cap serve

# 5. Test on device/emulator
npx cap run android
```

### 2. Building for Production

```bash
# Build optimized mobile assets
npm run mobile:build

# Sync with Android
npx cap sync android

# Open in Android Studio to build APK/AAB
npx cap open android
```

## Installation Requirements

### For Android Development

1. **Android Studio** (latest version)
2. **Android SDK** (API level 21+)
3. **Java Development Kit** (JDK 11 or higher)

### For iOS Development (Mac only)

1. **Xcode** (latest version)
2. **iOS SDK** (iOS 13+)
3. **Apple Developer Account** (for distribution)

## Configuration

### App Settings

Edit `capacitor.config.json` to customize:

```json
{
  "appId": "com.webtado.cmsvs",
  "appName": "إرشيف - الدفاع المدني",
  "webDir": "www",
  "server": {
    "androidScheme": "https",
    "allowNavigation": ["https://www.webtado.live"]
  }
}
```

### Android Settings

- **App Name**: Edit `android/app/src/main/res/values/strings.xml`
- **Permissions**: Edit `android/app/src/main/AndroidManifest.xml`
- **Icons**: Replace files in `android/app/src/main/res/mipmap-*/`

## Building APK/AAB

### Method 1: Using Android Studio (Recommended)

1. Open Android Studio
2. Open the `android` folder as a project
3. Build → Generate Signed Bundle/APK
4. Follow the wizard to create keystore and build

### Method 2: Using Command Line

```bash
# Navigate to android directory
cd android

# Build debug APK
./gradlew assembleDebug

# Build release APK (requires signing)
./gradlew assembleRelease

# Build App Bundle (for Play Store)
./gradlew bundleRelease
```

## Testing

### 1. Browser Testing

```bash
# Serve mobile app in browser
npx cap serve
```

### 2. Device Testing

```bash
# Run on connected Android device
npx cap run android

# Run on iOS device (Mac only)
npx cap run ios
```

### 3. Emulator Testing

```bash
# Run on Android emulator
npx cap run android --target=emulator

# Run on iOS simulator (Mac only)
npx cap run ios --target=simulator
```

## Deployment

### Google Play Store

1. Build signed AAB file
2. Create Google Play Console account
3. Upload AAB and complete store listing
4. Submit for review

### Apple App Store

1. Build signed IPA file
2. Create Apple Developer account
3. Upload to App Store Connect
4. Submit for review

## Troubleshooting

### Common Issues

1. **Build Errors**
   - Ensure Android SDK is properly installed
   - Check Java version compatibility
   - Clean and rebuild: `./gradlew clean`

2. **Sync Issues**
   - Delete `www` folder and rebuild: `npm run mobile:build`
   - Re-sync: `npx cap sync android`

3. **Plugin Issues**
   - Update Capacitor: `npm update @capacitor/core @capacitor/cli`
   - Reinstall plugins: `npm install`

### Logs and Debugging

```bash
# View Android logs
npx cap run android --livereload --external

# View iOS logs (Mac only)
npx cap run ios --livereload --external
```

## Maintenance

### Regular Updates

1. **Update Capacitor**
   ```bash
   npm update @capacitor/core @capacitor/cli
   npx cap sync
   ```

2. **Update Plugins**
   ```bash
   npm update @capacitor/android @capacitor/ios
   ```

3. **Update Dependencies**
   ```bash
   npm update
   ```

## Next Steps

### Potential Enhancements

1. **Biometric Authentication**
   - Add fingerprint/face recognition
   - Secure local storage

2. **Advanced Offline Features**
   - Local database (SQLite)
   - Conflict resolution
   - Background sync

3. **Performance Optimization**
   - Image optimization
   - Lazy loading
   - Bundle splitting

4. **Analytics and Monitoring**
   - Crash reporting
   - Usage analytics
   - Performance monitoring

## Support

For issues and questions:
1. Check Capacitor documentation: https://capacitorjs.com/docs
2. Review Android/iOS platform guides
3. Check the mobile API endpoints in your FastAPI backend

## Security Considerations

1. **API Security**
   - All mobile API calls use authentication tokens
   - HTTPS enforced for all communications
   - Input validation on all endpoints

2. **Data Protection**
   - Sensitive data encrypted in transit
   - Local storage secured
   - Push notifications don't contain sensitive data

3. **App Store Compliance**
   - Privacy policy required
   - Data usage disclosure
   - Security review compliance
