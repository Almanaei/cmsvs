const fs = require('fs');
const path = require('path');

// Configuration
const config = {
    sourceDir: 'app',
    outputDir: 'www',
    staticDir: 'app/static',
    templatesDir: 'app/templates',
    apiBaseUrl: process.env.API_BASE_URL || 'https://www.webtado.live'
};

// Ensure output directory exists
function ensureDir(dir) {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
        console.log(`Created directory: ${dir}`);
    }
}

// Copy static files
function copyStaticFiles() {
    console.log('Copying static files...');
    
    const staticSrc = config.staticDir;
    const staticDest = path.join(config.outputDir, 'static');
    
    ensureDir(staticDest);
    
    // Copy CSS, JS, images, etc.
    copyRecursive(staticSrc, staticDest);
    console.log('Static files copied successfully');
}

// Recursive copy function
function copyRecursive(src, dest) {
    if (!fs.existsSync(src)) {
        console.warn(`Source directory does not exist: ${src}`);
        return;
    }
    
    ensureDir(dest);
    
    const items = fs.readdirSync(src);
    
    items.forEach(item => {
        const srcPath = path.join(src, item);
        const destPath = path.join(dest, item);
        
        const stat = fs.statSync(srcPath);
        
        if (stat.isDirectory()) {
            copyRecursive(srcPath, destPath);
        } else {
            fs.copyFileSync(srcPath, destPath);
        }
    });
}

// Create a basic mobile-optimized index.html
function createMobileIndex() {
    console.log('Creating mobile index.html...');
    
    const indexContent = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta name="format-detection" content="telephone=no">
    <meta name="msapplication-tap-highlight" content="no">
    
    <title>إرشيف - الدفاع المدني</title>
    
    <!-- Capacitor Core -->
    <script type="module" src="https://unpkg.com/@capacitor/core@latest/dist/capacitor.js"></script>
    
    <!-- Status Bar -->
    <meta name="theme-color" content="#1f2937">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    
    <!-- App Icons -->
    <link rel="icon" type="image/png" href="static/logo_cmsvs.png">
    <link rel="apple-touch-icon" href="static/logo_cmsvs.png">
    
    <!-- Tailwind CSS -->
    <link rel="stylesheet" href="static/css/style.css">
    
    <!-- Mobile-specific styles -->
    <style>
        /* Mobile app specific styles */
        body {
            padding-top: env(safe-area-inset-top);
            padding-bottom: env(safe-area-inset-bottom);
            padding-left: env(safe-area-inset-left);
            padding-right: env(safe-area-inset-right);
        }
        
        /* Hide web-only elements in mobile app */
        .web-only {
            display: none !important;
        }
        
        /* Mobile app loading screen */
        .loading-screen {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: #1f2937;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }
        
        .loading-screen.hidden {
            display: none;
        }
    </style>
</head>
<body class="bg-gray-100">
    <!-- Loading Screen -->
    <div id="loading-screen" class="loading-screen">
        <div class="text-center text-white">
            <img src="static/logo_cmsvs.png" alt="Logo" class="w-20 h-20 mx-auto mb-4">
            <h1 class="text-xl font-bold mb-2">إرشيف</h1>
            <p class="text-gray-300">الدفاع المدني</p>
            <div class="mt-4">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto"></div>
            </div>
        </div>
    </div>
    
    <!-- App Container -->
    <div id="app-container" class="hidden">
        <!-- This will be populated by the mobile app logic -->
        <div class="min-h-screen bg-gray-100">
            <div class="container mx-auto px-4 py-8">
                <div class="text-center">
                    <img src="static/logo_cmsvs.png" alt="Logo" class="w-24 h-24 mx-auto mb-6">
                    <h1 class="text-3xl font-bold text-gray-800 mb-2">إرشيف</h1>
                    <p class="text-gray-600 mb-8">الدفاع المدني</p>
                    
                    <div class="space-y-4">
                        <button id="login-btn" class="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-700 transition-colors">
                            تسجيل الدخول
                        </button>
                        
                        <div class="text-sm text-gray-500">
                            نسخة الهاتف المحمول
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Mobile App JavaScript -->
    <script>
        // Mobile app configuration
        const APP_CONFIG = {
            apiBaseUrl: '${config.apiBaseUrl}',
            isNativeApp: true
        };
        
        // Initialize Capacitor
        document.addEventListener('DOMContentLoaded', async () => {
            // Import Capacitor plugins
            const { Capacitor } = await import('https://unpkg.com/@capacitor/core@latest/dist/capacitor.js');
            
            if (Capacitor.isNativePlatform()) {
                // Initialize native plugins
                try {
                    const { StatusBar } = await import('https://unpkg.com/@capacitor/status-bar@latest/dist/index.js');
                    const { App } = await import('https://unpkg.com/@capacitor/app@latest/dist/index.js');
                    
                    // Configure status bar
                    await StatusBar.setStyle({ style: 'DARK' });
                    await StatusBar.setBackgroundColor({ color: '#1f2937' });
                    
                    console.log('Native plugins initialized');
                } catch (error) {
                    console.warn('Some native plugins failed to initialize:', error);
                }
            }
            
            // Hide loading screen and show app
            setTimeout(() => {
                document.getElementById('loading-screen').classList.add('hidden');
                document.getElementById('app-container').classList.remove('hidden');
            }, 2000);
            
            // Set up login button
            document.getElementById('login-btn').addEventListener('click', () => {
                // Navigate to login page
                window.location.href = APP_CONFIG.apiBaseUrl + '/auth/login';
            });
        });
        
        // Handle back button on Android
        document.addEventListener('ionBackButton', (ev) => {
            ev.detail.register(-1, () => {
                if (window.location.pathname === '/') {
                    // Exit app
                    navigator.app.exitApp();
                } else {
                    // Go back
                    window.history.back();
                }
            });
        });
    </script>
</body>
</html>`;
    
    fs.writeFileSync(path.join(config.outputDir, 'index.html'), indexContent);
    console.log('Mobile index.html created successfully');

    // Copy PWA manifest if it exists
    const manifestSrc = path.join(config.outputDir, 'manifest.json');
    if (fs.existsSync(manifestSrc)) {
        console.log('PWA manifest already exists');
    } else {
        console.log('PWA manifest not found - PWA features may be limited');
    }
}

// Main build function
function buildMobile() {
    console.log('Starting mobile build process...');
    
    // Ensure output directory exists
    ensureDir(config.outputDir);
    
    // Copy static files
    copyStaticFiles();
    
    // Create mobile index
    createMobileIndex();
    
    console.log('Mobile build completed successfully!');
    console.log(`Output directory: ${config.outputDir}`);
}

// Run the build
buildMobile();
