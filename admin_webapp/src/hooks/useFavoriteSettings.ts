import { useState, useEffect, useCallback } from 'react';
import { STORAGE_KEYS } from '../config/constants';

const STORAGE_KEY = STORAGE_KEYS.FAVORITE_SETTINGS;

export function useFavoriteSettings() {
  const [favorites, setFavorites] = useState<string[]>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  // Sync to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites));
    } catch {
      // Ignore storage errors
    }
  }, [favorites]);

  const toggleFavorite = useCallback((settingKey: string) => {
    setFavorites((prev) => {
      if (prev.includes(settingKey)) {
        return prev.filter((key) => key !== settingKey);
      } else {
        return [...prev, settingKey];
      }
    });
  }, []);

  const isFavorite = useCallback(
    (settingKey: string) => {
      return favorites.includes(settingKey);
    },
    [favorites],
  );

  const clearFavorites = useCallback(() => {
    setFavorites([]);
  }, []);

  return {
    favorites,
    toggleFavorite,
    isFavorite,
    clearFavorites,
    count: favorites.length,
  };
}
