"""
Cached MNR Service
High-performance MNR operations with Redis caching
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.services.reference_service import ReferenceService
from app.core.redis import cached, cache, CacheKeys, CacheTTL
import json
import logging

logger = logging.getLogger(__name__)

class CachedBevService(ReferenceService):
    """
    Enhanced MNR Service with Redis caching for performance optimization
    Inherits from ReferenceService and adds caching layer for expensive operations
    """
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.cache = cache
    
    async def get_team_tree_cached(self, user_id: str, levels: int = 5) -> Dict[str, Any]:
        """Get binary tree with caching"""
        cache_key = CacheKeys.team_tree(user_id, levels)
        
        # Try cache first
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Get from database
        tree_data = self.get_team_tree(user_id, levels)
        
        # Cache the result
        await self.cache.set(cache_key, tree_data, CacheTTL.TEAM_TREE)
        
        return tree_data
    
    async def get_team_counts_cached(self, user_id: str) -> Dict[str, Any]:
        """Get team counts with caching"""
        cache_key = CacheKeys.team_counts(user_id)
        
        # Try cache first
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Get from database
        counts_data = self.get_team_counts(user_id)
        
        # Cache the result
        await self.cache.set(cache_key, counts_data, CacheTTL.TEAM_COUNTS)
        
        return counts_data
    
    async def get_comprehensive_income_summary_cached(self, user_id: str, month: Optional[str] = None) -> Dict[str, Any]:
        """Get income summary with caching"""
        if not month:
            month = self.get_indian_time().strftime("%Y-%m")
        
        cache_key = CacheKeys.income_summary(user_id, month)
        
        # Try cache first
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Get from database
        income_data = self.get_comprehensive_income_summary(user_id, month)
        
        # Cache the result
        await self.cache.set(cache_key, income_data, CacheTTL.INCOME_SUMMARY)
        
        return income_data
    
    async def get_user_placement_path_cached(self, user_id: str) -> List[Dict[str, Any]]:
        """Get placement path with caching (rarely changes)"""
        cache_key = CacheKeys.placement_path(user_id)
        
        # Try cache first
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Get placement path (this is expensive for deep trees)
        placement_path = self._get_placement_path_to_root(user_id)
        
        # Cache the result for longer since placement rarely changes
        await self.cache.set(cache_key, placement_path, CacheTTL.PLACEMENT_PATH)
        
        return placement_path
    
    def _get_placement_path_to_root(self, user_id: str) -> List[Dict[str, Any]]:
        """Get path from user to root of tree (expensive operation)"""
        path = []
        current_user_id = user_id
        
        # Traverse up the tree to root
        max_depth = 50  # Prevent infinite loops
        depth = 0
        
        while current_user_id and depth < max_depth:
            placement = self.get_user_placement_as_child(current_user_id)
            if not placement:
                break
            
            path.append({
                "user_id": current_user_id,
                "parent_id": placement.parent_id,
                "side": placement.side,
                "level": depth
            })
            
            current_user_id = placement.parent_id
            depth += 1
        
        return path
    
    async def invalidate_user_caches(self, user_id: str):
        """Invalidate all caches for a user (call when user data changes)"""
        await self.cache.invalidate_user_cache(user_id)
        
        # Also invalidate parent caches since team counts will change
        placement = self.get_user_placement_as_child(user_id)
        if placement and placement.parent_id:
            await self.invalidate_user_caches(placement.parent_id)
    
    async def invalidate_team_caches(self, user_id: str):
        """Invalidate team-related caches for a user and their upline"""
        # Get placement path to invalidate all upline caches
        try:
            placement_path = await self.get_user_placement_path_cached(user_id)
            
            # Invalidate caches for user and all parents
            for placement in placement_path:
                await self.cache.delete_pattern(f"reference:team_*:{placement['user_id']}:*")
                await self.cache.delete_pattern(f"reference:dashboard:{placement['user_id']}")
                
        except Exception as e:
            logger.error(f"Error invalidating team caches for {user_id}: {e}")
            # Fallback: just invalidate current user
            await self.cache.invalidate_user_cache(user_id)
    
    # Cache warming methods
    async def warm_user_cache(self, user_id: str):
        """Pre-populate cache for a user's common queries"""
        try:
            # Warm team data
            await self.get_team_counts_cached(user_id)
            await self.get_team_tree_cached(user_id, 3)  # Most common tree depth
            
            # Warm current month income
            current_month = self.get_indian_time().strftime("%Y-%m")
            await self.get_comprehensive_income_summary_cached(user_id, current_month)
            
            logger.info(f"Cache warmed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error warming cache for user {user_id}: {e}")
    
    async def warm_popular_caches(self):
        """Warm caches for the most active users"""
        try:
            # Get top 50 most active users (those with teams)
            active_users = self.db.execute("""
                SELECT DISTINCT p.parent_id 
                FROM placement p 
                WHERE p.parent_id IS NOT NULL 
                GROUP BY p.parent_id 
                HAVING COUNT(*) > 5
                LIMIT 50
            """).fetchall()
            
            # Warm their caches
            for user_row in active_users:
                user_id = user_row[0]
                await self.warm_user_cache(user_id)
            
            logger.info(f"Warmed caches for {len(active_users)} active users")
            
        except Exception as e:
            logger.error(f"Error warming popular caches: {e}")

# Factory function to create cached service
def get_cached_mnr_service(db: Session) -> CachedBevService:
    """Factory function to get cached Reference System service instance"""
    return CachedBevService(db)