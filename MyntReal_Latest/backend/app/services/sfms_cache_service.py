"""
SFMS Redis Cache Service
High-performance caching for Staff Financial Management System (SFMS)
Phase 3 Performance Optimization
"""

from typing import Any, Optional, List, Dict
from app.core.redis import cache, get_redis_client
import logging
import json

logger = logging.getLogger(__name__)

class SFMSCacheKeys:
    """Standardized cache keys for SFMS operations"""
    
    @staticmethod
    def stock_items_list(company_id: int, search: str = "", page: int = 1, page_size: int = 20) -> str:
        search_key = search.lower().strip() if search else "all"
        return f"sfms:stock_items:{company_id}:{search_key}:{page}:{page_size}"
    
    @staticmethod
    def stock_item_detail(item_id: int) -> str:
        return f"sfms:stock_item:{item_id}"
    
    @staticmethod
    def vendors_list(search: str = "", page: int = 1, page_size: int = 20, vendor_type: str = None) -> str:
        search_key = search.lower().strip() if search else "all"
        type_key = vendor_type or "all"
        return f"sfms:vendors:{type_key}:{search_key}:{page}:{page_size}"
    
    @staticmethod
    def vendor_detail(vendor_id: int) -> str:
        return f"sfms:vendor:{vendor_id}"
    
    @staticmethod
    def hsn_codes_list(search: str = "", page: int = 1, page_size: int = 20) -> str:
        search_key = search.lower().strip() if search else "all"
        return f"sfms:hsn_codes:{search_key}:{page}:{page_size}"
    
    @staticmethod
    def hsn_code_detail(code: str) -> str:
        return f"sfms:hsn:{code}"


class SFMSCacheTTL:
    """Cache TTL configurations for SFMS (in seconds)"""
    STOCK_ITEMS_LIST = 180      # 3 minutes - frequently searched
    STOCK_ITEM_DETAIL = 300     # 5 minutes - moderate changes
    VENDORS_LIST = 180          # 3 minutes - frequently searched
    VENDOR_DETAIL = 300         # 5 minutes - moderate changes
    HSN_CODES_LIST = 600        # 10 minutes - rarely changes
    HSN_CODE_DETAIL = 1800      # 30 minutes - almost never changes


class SFMSCacheService:
    """
    Redis caching service for SFMS operations
    Provides company-scoped caching for DC Protocol compliance
    """
    
    def __init__(self):
        self.cache = cache
    
    async def get_stock_items_cached(
        self,
        company_id: int,
        search: str = "",
        page: int = 1,
        page_size: int = 20
    ) -> Optional[Dict[str, Any]]:
        """Get cached stock items list"""
        cache_key = SFMSCacheKeys.stock_items_list(company_id, search, page, page_size)
        return await self.cache.get(cache_key)
    
    async def set_stock_items_cached(
        self,
        company_id: int,
        search: str,
        page: int,
        page_size: int,
        data: Dict[str, Any]
    ) -> bool:
        """Cache stock items list result"""
        cache_key = SFMSCacheKeys.stock_items_list(company_id, search, page, page_size)
        return await self.cache.set(cache_key, data, SFMSCacheTTL.STOCK_ITEMS_LIST)
    
    async def get_vendors_cached(
        self,
        search: str = "",
        page: int = 1,
        page_size: int = 20,
        vendor_type: str = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached vendors list"""
        cache_key = SFMSCacheKeys.vendors_list(search, page, page_size, vendor_type)
        return await self.cache.get(cache_key)
    
    async def set_vendors_cached(
        self,
        search: str,
        page: int,
        page_size: int,
        vendor_type: str,
        data: Dict[str, Any]
    ) -> bool:
        """Cache vendors list result"""
        cache_key = SFMSCacheKeys.vendors_list(search, page, page_size, vendor_type)
        return await self.cache.set(cache_key, data, SFMSCacheTTL.VENDORS_LIST)
    
    async def get_hsn_codes_cached(
        self,
        search: str = "",
        page: int = 1,
        page_size: int = 20
    ) -> Optional[Dict[str, Any]]:
        """Get cached HSN codes list"""
        cache_key = SFMSCacheKeys.hsn_codes_list(search, page, page_size)
        return await self.cache.get(cache_key)
    
    async def set_hsn_codes_cached(
        self,
        search: str,
        page: int,
        page_size: int,
        data: Dict[str, Any]
    ) -> bool:
        """Cache HSN codes list result"""
        cache_key = SFMSCacheKeys.hsn_codes_list(search, page, page_size)
        return await self.cache.set(cache_key, data, SFMSCacheTTL.HSN_CODES_LIST)
    
    async def invalidate_stock_items(self, company_id: int = None):
        """
        Invalidate stock items cache
        If company_id provided, invalidate only that company's cache
        """
        if company_id:
            pattern = f"sfms:stock_items:{company_id}:*"
        else:
            pattern = "sfms:stock_items:*"
        
        deleted = await self.cache.delete_pattern(pattern)
        logger.info(f"[SFMS-CACHE] Invalidated {deleted} stock items cache entries")
        return deleted
    
    async def invalidate_vendors(self):
        """Invalidate all vendors cache"""
        pattern = "sfms:vendors:*"
        deleted = await self.cache.delete_pattern(pattern)
        logger.info(f"[SFMS-CACHE] Invalidated {deleted} vendors cache entries")
        return deleted
    
    async def invalidate_hsn_codes(self):
        """Invalidate all HSN codes cache"""
        pattern = "sfms:hsn*"
        deleted = await self.cache.delete_pattern(pattern)
        logger.info(f"[SFMS-CACHE] Invalidated {deleted} HSN cache entries")
        return deleted
    
    async def invalidate_all_sfms(self):
        """Invalidate all SFMS caches"""
        pattern = "sfms:*"
        deleted = await self.cache.delete_pattern(pattern)
        logger.info(f"[SFMS-CACHE] Invalidated ALL SFMS cache: {deleted} entries")
        return deleted
    
    def is_cache_available(self) -> bool:
        """Check if Redis cache is available"""
        return get_redis_client() is not None


sfms_cache = SFMSCacheService()
