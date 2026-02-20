// Offline-first storage utilities using IndexedDB

const DB_NAME = 'AcollyaDB';
const DB_VERSION = 1;
const STORES = {
  moodCheckins: 'moodCheckins',
  journalEntries: 'journalEntries',
  chatMessages: 'chatMessages',
  pendingSync: 'pendingSync',
};

let db: IDBDatabase | null = null;

export async function initDB(): Promise<IDBDatabase> {
  if (db) return db;

  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      db = request.result;
      resolve(db);
    };

    request.onupgradeneeded = (event) => {
      const database = (event.target as IDBOpenDBRequest).result;

      // Create object stores
      if (!database.objectStoreNames.contains(STORES.moodCheckins)) {
        database.createObjectStore(STORES.moodCheckins, { keyPath: 'id' });
      }
      if (!database.objectStoreNames.contains(STORES.journalEntries)) {
        database.createObjectStore(STORES.journalEntries, { keyPath: 'id' });
      }
      if (!database.objectStoreNames.contains(STORES.chatMessages)) {
        database.createObjectStore(STORES.chatMessages, { keyPath: 'id' });
      }
      if (!database.objectStoreNames.contains(STORES.pendingSync)) {
        database.createObjectStore(STORES.pendingSync, { keyPath: 'id', autoIncrement: true });
      }
    };
  });
}

export async function saveOfflineData(storeName: string, data: Record<string, unknown>): Promise<void> {
  const database = await initDB();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction([storeName], 'readwrite');
    const store = transaction.objectStore(storeName);
    const request = store.put(data);

    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

export async function getOfflineData(storeName: string): Promise<Record<string, unknown>[]> {
  const database = await initDB();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction([storeName], 'readonly');
    const store = transaction.objectStore(storeName);
    const request = store.getAll();

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function addPendingSync(action: string, data: Record<string, unknown>): Promise<void> {
  const database = await initDB();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction([STORES.pendingSync], 'readwrite');
    const store = transaction.objectStore(STORES.pendingSync);
    const request = store.add({
      action,
      data,
      timestamp: new Date().toISOString(),
    });

    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

export async function getPendingSync(): Promise<Record<string, unknown>[]> {
  return getOfflineData(STORES.pendingSync);
}

export async function clearPendingSync(): Promise<void> {
  const database = await initDB();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction([STORES.pendingSync], 'readwrite');
    const store = transaction.objectStore(STORES.pendingSync);
    const request = store.clear();

    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}