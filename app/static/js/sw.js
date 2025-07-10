/**
 * CMSVS Service Worker for Push Notifications
 * Handles background push notifications and click events
 */

const CACHE_NAME = 'cmsvs-notifications-v1';
const urlsToCache = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/icons/notification-icon.png',
    '/static/icons/badge-icon.png'
];

// Install event - cache resources
self.addEventListener('install', function(event) {
    console.log('Service Worker installing...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(function(cache) {
                console.log('Opened cache');
                return cache.addAll(urlsToCache);
            })
            .catch(function(error) {
                console.error('Cache installation failed:', error);
            })
    );
    
    // Skip waiting to activate immediately
    self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', function(event) {
    console.log('Service Worker activating...');
    
    event.waitUntil(
        caches.keys().then(function(cacheNames) {
            return Promise.all(
                cacheNames.map(function(cacheName) {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    
    // Claim all clients immediately
    return self.clients.claim();
});

// Push event - handle incoming push notifications
self.addEventListener('push', function(event) {
    console.log('Push notification received:', event);
    
    let notificationData = {
        title: 'إرشيف - إشعار جديد',
        body: 'لديك إشعار جديد',
        icon: '/static/icons/notification-icon.png',
        badge: '/static/icons/badge-icon.png',
        data: {
            url: '/',
            timestamp: Date.now()
        },
        actions: [
            {
                action: 'view',
                title: 'عرض',
                icon: '/static/icons/view-icon.png'
            },
            {
                action: 'dismiss',
                title: 'إغلاق',
                icon: '/static/icons/close-icon.png'
            }
        ],
        requireInteraction: true,
        silent: false,
        tag: 'cmsvs-notification',
        renotify: true
    };
    
    // Parse notification data if available
    if (event.data) {
        try {
            const payload = event.data.json();
            notificationData = { ...notificationData, ...payload };
        } catch (error) {
            console.error('Error parsing push data:', error);
            notificationData.body = event.data.text() || notificationData.body;
        }
    }
    
    // Show notification
    event.waitUntil(
        self.registration.showNotification(notificationData.title, {
            body: notificationData.body,
            icon: notificationData.icon,
            badge: notificationData.badge,
            data: notificationData.data,
            actions: notificationData.actions,
            requireInteraction: notificationData.requireInteraction,
            silent: notificationData.silent,
            tag: notificationData.tag,
            renotify: notificationData.renotify,
            dir: 'rtl', // Right-to-left for Arabic text
            lang: 'ar'
        })
    );
});

// Notification click event - handle user interaction
self.addEventListener('notificationclick', function(event) {
    console.log('Notification clicked:', event);
    
    const notification = event.notification;
    const action = event.action;
    const data = notification.data || {};
    
    // Close the notification
    notification.close();
    
    // Handle different actions
    if (action === 'dismiss') {
        // Just close the notification
        return;
    }
    
    // Default action or 'view' action - open the app
    const urlToOpen = data.url || '/';
    
    event.waitUntil(
        clients.matchAll({
            type: 'window',
            includeUncontrolled: true
        }).then(function(clientList) {
            // Check if app is already open
            for (let i = 0; i < clientList.length; i++) {
                const client = clientList[i];
                const clientUrl = new URL(client.url);
                const targetUrl = new URL(urlToOpen, self.location.origin);
                
                // If app is open, focus it and navigate
                if (clientUrl.origin === targetUrl.origin) {
                    if (client.url !== targetUrl.href) {
                        client.navigate(targetUrl.href);
                    }
                    return client.focus();
                }
            }
            
            // If app is not open, open new window
            return clients.openWindow(urlToOpen);
        })
    );
});

// Background sync event (for future use)
self.addEventListener('sync', function(event) {
    console.log('Background sync:', event);
    
    if (event.tag === 'background-sync') {
        event.waitUntil(
            // Perform background sync operations
            doBackgroundSync()
        );
    }
});

// Message event - handle messages from main thread
self.addEventListener('message', function(event) {
    console.log('Service Worker received message:', event.data);
    
    const data = event.data;
    
    if (data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    } else if (data.type === 'GET_VERSION') {
        event.ports[0].postMessage({ version: CACHE_NAME });
    } else if (data.type === 'CLEAR_CACHE') {
        event.waitUntil(
            caches.delete(CACHE_NAME).then(function() {
                event.ports[0].postMessage({ success: true });
            })
        );
    }
});

// Fetch event - handle network requests (basic caching strategy)
self.addEventListener('fetch', function(event) {
    // Only handle GET requests
    if (event.request.method !== 'GET') {
        return;
    }
    
    // Skip non-HTTP requests
    if (!event.request.url.startsWith('http')) {
        return;
    }
    
    event.respondWith(
        caches.match(event.request)
            .then(function(response) {
                // Return cached version if available
                if (response) {
                    return response;
                }
                
                // Otherwise fetch from network
                return fetch(event.request).then(function(response) {
                    // Don't cache if not a valid response
                    if (!response || response.status !== 200 || response.type !== 'basic') {
                        return response;
                    }
                    
                    // Clone the response
                    const responseToCache = response.clone();
                    
                    // Cache static resources
                    if (event.request.url.includes('/static/')) {
                        caches.open(CACHE_NAME)
                            .then(function(cache) {
                                cache.put(event.request, responseToCache);
                            });
                    }
                    
                    return response;
                });
            })
            .catch(function(error) {
                console.error('Fetch failed:', error);
                
                // Return offline page for navigation requests
                if (event.request.mode === 'navigate') {
                    return caches.match('/offline.html');
                }
                
                throw error;
            })
    );
});

// Background sync function
async function doBackgroundSync() {
    try {
        console.log('Performing background sync...');
        
        // Sync pending notifications
        const response = await fetch('/api/notifications/sync', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (response.ok) {
            console.log('Background sync completed successfully');
        } else {
            console.error('Background sync failed:', response.status);
        }
        
    } catch (error) {
        console.error('Background sync error:', error);
        throw error;
    }
}

// Notification close event
self.addEventListener('notificationclose', function(event) {
    console.log('Notification closed:', event.notification.tag);
    
    // Track notification dismissal (optional)
    const data = event.notification.data || {};
    
    if (data.trackDismissal) {
        fetch('/api/notifications/track-dismissal', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                notificationId: data.notificationId,
                timestamp: Date.now()
            })
        }).catch(error => {
            console.error('Error tracking notification dismissal:', error);
        });
    }
});

// Error event
self.addEventListener('error', function(event) {
    console.error('Service Worker error:', event.error);
});

// Unhandled rejection event
self.addEventListener('unhandledrejection', function(event) {
    console.error('Service Worker unhandled rejection:', event.reason);
});

console.log('CMSVS Service Worker loaded successfully');
