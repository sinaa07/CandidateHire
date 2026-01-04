import type { Collection } from "@/types"

const COLLECTIONS_KEY = "candidatehire_collections"

export function getCollectionsFromStorage(): Collection[] {
  try {
    const stored = localStorage.getItem(COLLECTIONS_KEY)
    return stored ? JSON.parse(stored) : []
  } catch {
    return []
  }
}

export function saveCollectionToStorage(collection: Collection) {
  try {
    const collections = getCollectionsFromStorage()
    const index = collections.findIndex((c) => c.id === collection.id)
    if (index >= 0) {
      collections[index] = collection
    } else {
      collections.unshift(collection)
    }
    localStorage.setItem(COLLECTIONS_KEY, JSON.stringify(collections.slice(0, 10))) // Keep last 10
  } catch (error) {
    console.error("Failed to save collection:", error)
  }
}

export function updateCollectionLastAccessed(collectionId: string) {
  try {
    const collections = getCollectionsFromStorage()
    const collection = collections.find((c) => c.id === collectionId)
    if (collection) {
      collection.last_accessed = new Date().toISOString()
      localStorage.setItem(COLLECTIONS_KEY, JSON.stringify(collections))
    }
  } catch (error) {
    console.error("Failed to update collection:", error)
  }
}
