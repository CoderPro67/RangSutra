# Embedding cache
"""
Cache Manager Module
Handles caching of embeddings and computed features for performance.
"""

import os
import pickle
import hashlib
import json
from typing import Any, Optional
from pathlib import Path


class CacheManager:
    """
    Manages persistent cache for embeddings and features.
    """
    
    def __init__(self, cache_dir: str = "models/embeddings"):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_index_path = os.path.join(cache_dir, 'cache_index.json')
        self.cache_index = self._load_index()
    
    def _load_index(self) -> dict:
        """Load cache index from disk."""
        if os.path.exists(self.cache_index_path):
            try:
                with open(self.cache_index_path, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_index(self):
        """Save cache index to disk."""
        with open(self.cache_index_path, 'w') as f:
            json.dump(self.cache_index, f, indent=2)
    
    def _get_cache_key(self, data: str, prefix: str = "") -> str:
        """
        Generate cache key from data.
        
        Args:
            data: Data to hash
            prefix: Optional prefix for cache key
            
        Returns:
            Cache key string
        """
        hash_obj = hashlib.sha256(data.encode())
        return f"{prefix}_{hash_obj.hexdigest()[:16]}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached object or None if not found
        """
        if key not in self.cache_index:
            return None
        
        cache_file = self.cache_index[key]['file']
        cache_path = os.path.join(self.cache_dir, cache_file)
        
        if not os.path.exists(cache_path):
            # Remove stale index entry
            del self.cache_index[key]
            self._save_index()
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"⚠ Cache read error: {e}")
            return None
    
    def set(self, key: str, value: Any, metadata: dict = None):
        """
        Store item in cache.
        
        Args:
            key: Cache key
            value: Object to cache
            metadata: Optional metadata
        """
        cache_file = f"{key}.pkl"
        cache_path = os.path.join(self.cache_dir, cache_file)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            # Update index
            self.cache_index[key] = {
                'file': cache_file,
                'metadata': metadata or {}
            }
            self._save_index()
            
        except Exception as e:
            print(f"⚠ Cache write error: {e}")
    
    def has(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self.cache_index
    
    def delete(self, key: str):
        """Delete item from cache."""
        if key in self.cache_index:
            cache_file = self.cache_index[key]['file']
            cache_path = os.path.join(self.cache_dir, cache_file)
            
            if os.path.exists(cache_path):
                os.remove(cache_path)
            
            del self.cache_index[key]
            self._save_index()
    
    def clear(self):
        """Clear all cache entries."""
        for key in list(self.cache_index.keys()):
            self.delete(key)
    
    def get_cache_size(self) -> int:
        """Get total cache size in bytes."""
        total_size = 0
        for key, info in self.cache_index.items():
            cache_file = info['file']
            cache_path = os.path.join(self.cache_dir, cache_file)
            if os.path.exists(cache_path):
                total_size += os.path.getsize(cache_path)
        return total_size
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            'total_entries': len(self.cache_index),
            'total_size_mb': self.get_cache_size() / (1024 * 1024),
            'cache_dir': self.cache_dir
        }