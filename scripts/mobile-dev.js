#!/usr/bin/env node

/**
 * Mobile Development Helper Script for CMSVS
 * 
 * This script provides convenient commands for mobile app development
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Colors for console output
const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m'
};

function log(message, color = 'reset') {
    console.log(`${colors[color]}${message}${colors.reset}`);
}

function execCommand(command, description) {
    log(`\n${description}...`, 'cyan');
    try {
        execSync(command, { stdio: 'inherit' });
        log(`✅ ${description} completed successfully`, 'green');
        return true;
    } catch (error) {
        log(`❌ ${description} failed`, 'red');
        console.error(error.message);
        return false;
    }
}

function showHelp() {
    log('\n📱 CMSVS Mobile Development Helper', 'bright');
    log('=====================================', 'bright');
    log('\nAvailable commands:', 'yellow');
    log('  build     - Build mobile assets and sync with native projects');
    log('  android   - Open Android project in Android Studio');
    log('  ios       - Add iOS platform and open in Xcode (Mac only)');
    log('  serve     - Serve mobile app in browser for testing');
    log('  run-android - Run app on Android device/emulator');
    log('  run-ios   - Run app on iOS device/simulator (Mac only)');
    log('  clean     - Clean build artifacts and rebuild');
    log('  status    - Show project status and configuration');
    log('  help      - Show this help message');
    log('\nExamples:', 'yellow');
    log('  node scripts/mobile-dev.js build');
    log('  node scripts/mobile-dev.js run-android');
    log('  node scripts/mobile-dev.js serve\n');
}

function showStatus() {
    log('\n📊 CMSVS Mobile App Status', 'bright');
    log('==========================', 'bright');
    
    // Check if Capacitor is configured
    const capacitorConfig = path.join(process.cwd(), 'capacitor.config.json');
    if (fs.existsSync(capacitorConfig)) {
        const config = JSON.parse(fs.readFileSync(capacitorConfig, 'utf8'));
        log(`\n✅ App ID: ${config.appId}`, 'green');
        log(`✅ App Name: ${config.appName}`, 'green');
        log(`✅ Web Directory: ${config.webDir}`, 'green');
    } else {
        log('\n❌ Capacitor not configured', 'red');
        return;
    }
    
    // Check platforms
    const androidDir = path.join(process.cwd(), 'android');
    const iosDir = path.join(process.cwd(), 'ios');
    
    log('\n📱 Platforms:', 'yellow');
    log(`  Android: ${fs.existsSync(androidDir) ? '✅ Configured' : '❌ Not added'}`, 
        fs.existsSync(androidDir) ? 'green' : 'red');
    log(`  iOS: ${fs.existsSync(iosDir) ? '✅ Configured' : '❌ Not added'}`, 
        fs.existsSync(iosDir) ? 'green' : 'red');
    
    // Check www directory
    const wwwDir = path.join(process.cwd(), 'www');
    log(`\n📁 Build Output: ${fs.existsSync(wwwDir) ? '✅ Ready' : '❌ Not built'}`, 
        fs.existsSync(wwwDir) ? 'green' : 'red');
    
    // Check package.json scripts
    const packageJson = path.join(process.cwd(), 'package.json');
    if (fs.existsSync(packageJson)) {
        const pkg = JSON.parse(fs.readFileSync(packageJson, 'utf8'));
        log('\n🔧 Available Scripts:', 'yellow');
        Object.keys(pkg.scripts || {}).forEach(script => {
            if (script.includes('mobile')) {
                log(`  ${script}: ${pkg.scripts[script]}`, 'cyan');
            }
        });
    }
    
    log('');
}

function buildMobile() {
    log('\n🔨 Building Mobile App', 'bright');
    log('======================', 'bright');
    
    // Build CSS
    if (!execCommand('npm run build-css-prod', 'Building Tailwind CSS')) {
        return false;
    }
    
    // Copy mobile assets
    if (!execCommand('npm run mobile:copy', 'Copying mobile assets')) {
        return false;
    }
    
    // Sync with Android
    if (fs.existsSync('android')) {
        if (!execCommand('npx cap sync android', 'Syncing with Android')) {
            return false;
        }
    }
    
    // Sync with iOS if available
    if (fs.existsSync('ios')) {
        if (!execCommand('npx cap sync ios', 'Syncing with iOS')) {
            return false;
        }
    }
    
    log('\n🎉 Mobile build completed successfully!', 'green');
    return true;
}

function cleanBuild() {
    log('\n🧹 Cleaning Build Artifacts', 'bright');
    log('============================', 'bright');
    
    // Remove www directory
    if (fs.existsSync('www')) {
        fs.rmSync('www', { recursive: true, force: true });
        log('✅ Removed www directory', 'green');
    }
    
    // Clean Android build
    if (fs.existsSync('android')) {
        try {
            execSync('cd android && ./gradlew clean', { stdio: 'inherit' });
            log('✅ Cleaned Android build', 'green');
        } catch (error) {
            log('⚠️  Could not clean Android build', 'yellow');
        }
    }
    
    // Rebuild
    return buildMobile();
}

function addIOS() {
    if (process.platform !== 'darwin') {
        log('❌ iOS development is only supported on macOS', 'red');
        return false;
    }
    
    log('\n🍎 Adding iOS Platform', 'bright');
    log('======================', 'bright');
    
    if (!execCommand('npx cap add ios', 'Adding iOS platform')) {
        return false;
    }
    
    if (!execCommand('npx cap open ios', 'Opening iOS project in Xcode')) {
        return false;
    }
    
    return true;
}

// Main command handler
function main() {
    const command = process.argv[2];
    
    switch (command) {
        case 'build':
            buildMobile();
            break;
            
        case 'android':
            execCommand('npx cap open android', 'Opening Android project');
            break;
            
        case 'ios':
            addIOS();
            break;
            
        case 'serve':
            execCommand('npx cap serve', 'Starting development server');
            break;
            
        case 'run-android':
            if (buildMobile()) {
                execCommand('npx cap run android', 'Running on Android');
            }
            break;
            
        case 'run-ios':
            if (process.platform !== 'darwin') {
                log('❌ iOS development is only supported on macOS', 'red');
                break;
            }
            if (buildMobile()) {
                execCommand('npx cap run ios', 'Running on iOS');
            }
            break;
            
        case 'clean':
            cleanBuild();
            break;
            
        case 'status':
            showStatus();
            break;
            
        case 'help':
        case '--help':
        case '-h':
            showHelp();
            break;
            
        default:
            if (command) {
                log(`❌ Unknown command: ${command}`, 'red');
            }
            showHelp();
            break;
    }
}

// Run the script
main();
