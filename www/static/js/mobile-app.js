// Mobile App Integration for CMSVS
class CMSVSMobileApp {
    constructor() {
        this.apiBaseUrl = 'https://www.webtado.live';
        this.isNative = false;
        this.plugins = {};
        this.init();
    }

    async init() {
        try {
            // Import Capacitor core
            const { Capacitor } = await import('https://unpkg.com/@capacitor/core@latest/dist/capacitor.js');
            this.isNative = Capacitor.isNativePlatform();
            
            if (this.isNative) {
                await this.initializeNativePlugins();
            }
            
            this.setupEventListeners();
            console.log('CMSVS Mobile App initialized');
        } catch (error) {
            console.error('Failed to initialize mobile app:', error);
        }
    }

    async initializeNativePlugins() {
        try {
            // Status Bar
            const { StatusBar } = await import('https://unpkg.com/@capacitor/status-bar@latest/dist/index.js');
            this.plugins.statusBar = StatusBar;
            await StatusBar.setStyle({ style: 'DARK' });
            await StatusBar.setBackgroundColor({ color: '#1f2937' });

            // App
            const { App } = await import('https://unpkg.com/@capacitor/app@latest/dist/index.js');
            this.plugins.app = App;

            // Push Notifications
            const { PushNotifications } = await import('https://unpkg.com/@capacitor/push-notifications@latest/dist/index.js');
            this.plugins.pushNotifications = PushNotifications;
            await this.setupPushNotifications();

            // Camera
            const { Camera } = await import('https://unpkg.com/@capacitor/camera@latest/dist/index.js');
            this.plugins.camera = Camera;

            // Filesystem
            const { Filesystem } = await import('https://unpkg.com/@capacitor/filesystem@latest/dist/index.js');
            this.plugins.filesystem = Filesystem;

            // Haptics
            const { Haptics } = await import('https://unpkg.com/@capacitor/haptics@latest/dist/index.js');
            this.plugins.haptics = Haptics;

            // Keyboard
            const { Keyboard } = await import('https://unpkg.com/@capacitor/keyboard@latest/dist/index.js');
            this.plugins.keyboard = Keyboard;

            console.log('Native plugins initialized successfully');
        } catch (error) {
            console.error('Failed to initialize native plugins:', error);
        }
    }

    async setupPushNotifications() {
        try {
            const permStatus = await this.plugins.pushNotifications.requestPermissions();
            
            if (permStatus.receive === 'granted') {
                await this.plugins.pushNotifications.register();
                
                // Listen for registration token
                this.plugins.pushNotifications.addListener('registration', (token) => {
                    console.log('Push registration token:', token.value);
                    this.sendTokenToServer(token.value);
                });

                // Listen for incoming notifications
                this.plugins.pushNotifications.addListener('pushNotificationReceived', (notification) => {
                    console.log('Push notification received:', notification);
                    this.handleIncomingNotification(notification);
                });

                // Listen for notification actions
                this.plugins.pushNotifications.addListener('pushNotificationActionPerformed', (notification) => {
                    console.log('Push notification action performed:', notification);
                    this.handleNotificationAction(notification);
                });
            }
        } catch (error) {
            console.error('Failed to setup push notifications:', error);
        }
    }

    async sendTokenToServer(token) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/mobile/register-token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify({ token, platform: 'android' })
            });
            
            if (response.ok) {
                console.log('Push token registered successfully');
            }
        } catch (error) {
            console.error('Failed to register push token:', error);
        }
    }

    handleIncomingNotification(notification) {
        // Handle incoming push notification
        if (this.plugins.haptics) {
            this.plugins.haptics.vibrate();
        }
        
        // You can add custom logic here to update the UI
        this.showInAppNotification(notification);
    }

    handleNotificationAction(notification) {
        // Handle notification tap/action
        const data = notification.notification.data;
        
        if (data && data.url) {
            // Navigate to specific page
            window.location.href = data.url;
        } else {
            // Default action - go to home
            window.location.href = '/';
        }
    }

    showInAppNotification(notification) {
        // Create in-app notification banner
        const banner = document.createElement('div');
        banner.className = 'fixed top-4 left-4 right-4 bg-blue-600 text-white p-4 rounded-lg shadow-lg z-50 transform -translate-y-full transition-transform duration-300';
        banner.innerHTML = `
            <div class="flex items-center justify-between">
                <div>
                    <h4 class="font-bold">${notification.title}</h4>
                    <p class="text-sm">${notification.body}</p>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" class="text-white">
                    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                    </svg>
                </button>
            </div>
        `;
        
        document.body.appendChild(banner);
        
        // Animate in
        setTimeout(() => {
            banner.style.transform = 'translateY(0)';
        }, 100);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            banner.style.transform = 'translateY(-100%)';
            setTimeout(() => banner.remove(), 300);
        }, 5000);
    }

    async takePicture() {
        if (!this.plugins.camera) {
            throw new Error('Camera plugin not available');
        }

        try {
            const image = await this.plugins.camera.getPhoto({
                quality: 90,
                allowEditing: false,
                resultType: 'DataUrl',
                source: 'Camera'
            });

            return image.dataUrl;
        } catch (error) {
            console.error('Failed to take picture:', error);
            throw error;
        }
    }

    async selectFromGallery() {
        if (!this.plugins.camera) {
            throw new Error('Camera plugin not available');
        }

        try {
            const image = await this.plugins.camera.getPhoto({
                quality: 90,
                allowEditing: false,
                resultType: 'DataUrl',
                source: 'Photos'
            });

            return image.dataUrl;
        } catch (error) {
            console.error('Failed to select from gallery:', error);
            throw error;
        }
    }

    async saveFile(data, filename) {
        if (!this.plugins.filesystem) {
            throw new Error('Filesystem plugin not available');
        }

        try {
            const result = await this.plugins.filesystem.writeFile({
                path: filename,
                data: data,
                directory: 'Documents'
            });

            return result.uri;
        } catch (error) {
            console.error('Failed to save file:', error);
            throw error;
        }
    }

    setupEventListeners() {
        // Handle app state changes
        if (this.plugins.app) {
            this.plugins.app.addListener('appStateChange', (state) => {
                console.log('App state changed:', state);
                if (state.isActive) {
                    // App became active - refresh data
                    this.refreshAppData();
                }
            });

            this.plugins.app.addListener('backButton', () => {
                // Handle back button
                if (window.location.pathname === '/' || window.location.pathname === '/index.html') {
                    this.plugins.app.exitApp();
                } else {
                    window.history.back();
                }
            });
        }

        // Handle keyboard events
        if (this.plugins.keyboard) {
            this.plugins.keyboard.addListener('keyboardWillShow', (info) => {
                document.body.style.paddingBottom = `${info.keyboardHeight}px`;
            });

            this.plugins.keyboard.addListener('keyboardWillHide', () => {
                document.body.style.paddingBottom = '0px';
            });
        }
    }

    async refreshAppData() {
        // Refresh app data when app becomes active
        try {
            // You can add logic here to refresh user data, notifications, etc.
            console.log('Refreshing app data...');
        } catch (error) {
            console.error('Failed to refresh app data:', error);
        }
    }

    getAuthToken() {
        // Get authentication token from localStorage or cookies
        return localStorage.getItem('auth_token') || '';
    }

    async makeAuthenticatedRequest(url, options = {}) {
        const token = this.getAuthToken();
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        try {
            const response = await fetch(`${this.apiBaseUrl}${url}`, mergedOptions);
            
            if (response.status === 401) {
                // Token expired - redirect to login
                window.location.href = `${this.apiBaseUrl}/auth/login`;
                return null;
            }
            
            return response;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }
}

// Initialize the mobile app
window.CMSVSMobileApp = new CMSVSMobileApp();
