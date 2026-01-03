/**
 * IndexedDB cache for Python modules and data files
 * Reduces load time on subsequent visits
 */

const DB_NAME = 'pso_optimizer_cache';
const DB_VERSION = 2; // Increment to force cache clear on schema change
const CACHE_STORE = 'files';
const VERSION_STORE = 'versions';
const VERSION_KEY = 'app_version';

let db = null;
let currentVersion = null;

/**
 * Initialize IndexedDB
 */
async function initCache() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            db = request.result;
            resolve(db);
        };

        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            const transaction = event.target.transaction;
            
            // Store for cached files
            if (!db.objectStoreNames.contains(CACHE_STORE)) {
                const fileStore = db.createObjectStore(CACHE_STORE, { keyPath: 'url' });
                fileStore.createIndex('timestamp', 'timestamp', { unique: false });
            }
            
            // Store for version tracking
            if (!db.objectStoreNames.contains(VERSION_STORE)) {
                db.createObjectStore(VERSION_STORE, { keyPath: 'key' });
            }
            
            // Clear cache on schema upgrade (only if upgrading from an older version)
            if (event.oldVersion > 0 && event.oldVersion < DB_VERSION) {
                const fileStore = transaction.objectStore(CACHE_STORE);
                fileStore.clear();
            }
        };
    });
}

/**
 * Get cached file if available and not expired
 */
async function getCached(url, maxAge = 7 * 24 * 60 * 60 * 1000) { // 7 days default
    if (!db) {
        await initCache();
    }

    return new Promise((resolve, reject) => {
        const transaction = db.transaction([CACHE_STORE], 'readonly');
        const store = transaction.objectStore(CACHE_STORE);
        const request = store.get(url);

        request.onsuccess = () => {
            const result = request.result;
            if (!result) {
                resolve(null);
                return;
            }

            const age = Date.now() - result.timestamp;
            if (age > maxAge) {
                // Cache expired, delete it
                deleteCached(url);
                resolve(null);
                return;
            }

            resolve(result.data);
        };

        request.onerror = () => {
            console.warn('Cache read error:', request.error);
            resolve(null); // Fail gracefully
        };
    });
}

/**
 * Cache a file
 */
async function setCached(url, data) {
    if (!db) {
        await initCache();
    }

    return new Promise((resolve, reject) => {
        const transaction = db.transaction([CACHE_STORE], 'readwrite');
        const store = transaction.objectStore(CACHE_STORE);
        const request = store.put({
            url: url,
            data: data,
            timestamp: Date.now(),
        });

        request.onsuccess = () => resolve();
        request.onerror = () => {
            console.warn('Cache write error:', request.error);
            resolve(); // Fail gracefully, don't block
        };
    });
}

/**
 * Delete a cached file
 */
async function deleteCached(url) {
    if (!db) {
        await initCache();
    }

    return new Promise((resolve) => {
        const transaction = db.transaction([CACHE_STORE], 'readwrite');
        const store = transaction.objectStore(CACHE_STORE);
        const request = store.delete(url);

        request.onsuccess = () => resolve();
        request.onerror = () => resolve(); // Fail gracefully
    });
}

/**
 * Clear all cached files
 */
async function clearCache() {
    if (!db) {
        await initCache();
    }

    return new Promise((resolve) => {
        const transaction = db.transaction([CACHE_STORE], 'readwrite');
        const store = transaction.objectStore(CACHE_STORE);
        const request = store.clear();

        request.onsuccess = () => resolve();
        request.onerror = () => resolve(); // Fail gracefully
    });
}

/**
 * Fetch text with cache support
 */
async function fetchTextWithCache(url) {
    // Try cache first
    const cached = await getCached(url);
    if (cached !== null) {
        return new TextDecoder().decode(cached);
    }

    // Fetch from network
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Failed to fetch ${url}: ${response.status} ${response.statusText}`);
    }

    // Cache the response
    const data = await response.arrayBuffer();
    await setCached(url, data);

    // Return the text
    return new TextDecoder().decode(data);
}

/**
 * Fetch JSON with cache support
 */
async function fetchJSONWithCache(url) {
    // Try cache first
    const cached = await getCached(url);
    if (cached !== null) {
        return JSON.parse(new TextDecoder().decode(cached));
    }

    // Fetch from network
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Failed to fetch ${url}: ${response.status} ${response.statusText}`);
    }

    // Cache the response
    const data = await response.arrayBuffer();
    await setCached(url, data);

    // Parse and return JSON
    return JSON.parse(new TextDecoder().decode(data));
}

/**
 * Check and update app version for cache busting
 * @param {string} basePath - Base path for fetching version.json
 */
async function checkVersion(basePath = './') {
    if (!db) {
        await initCache();
    }

    try {
        // Fetch current version from server (don't use cache for version check!)
        const response = await fetch(`${basePath}version.json`);
        if (!response.ok) {
            throw new Error(`Failed to fetch version: ${response.status}`);
        }
        const versionInfo = await response.json();
        const serverVersion = versionInfo.version;

        // Get stored version
        const storedVersion = await new Promise((resolve) => {
            const transaction = db.transaction([VERSION_STORE], 'readonly');
            const store = transaction.objectStore(VERSION_STORE);
            const request = store.get(VERSION_KEY);

            request.onsuccess = () => {
                resolve(request.result ? request.result.value : null);
            };
            request.onerror = () => resolve(null);
        });

        // If versions don't match, clear cache
        if (storedVersion !== serverVersion) {
            console.log(`Version mismatch: stored=${storedVersion}, server=${serverVersion}. Clearing cache.`);
            await clearCache();
            
            // Store new version
            await new Promise((resolve) => {
                const transaction = db.transaction([VERSION_STORE], 'readwrite');
                const store = transaction.objectStore(VERSION_STORE);
                const request = store.put({ key: VERSION_KEY, value: serverVersion });

                request.onsuccess = () => resolve();
                request.onerror = () => resolve(); // Fail gracefully
            });

            currentVersion = serverVersion;
            return true; // Cache was cleared
        }

        currentVersion = serverVersion;
        return false; // No cache clear needed
    } catch (error) {
        // If version.json doesn't exist (local dev), skip version check
        console.warn('Version check failed (this is OK for local development):', error);
        return false;
    }
}

