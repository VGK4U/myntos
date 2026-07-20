/**
 * Admin ID Utilities for MNR Reference Program
 * Handles normalization of legacy MNR IDs to MNR format
 * 
 * Migration Context: Database migrated from MNR to MNR format (Nov 2025)
 * Some cached data (sessionStorage, localStorage, bookmarks) may still contain MNR IDs
 * This utility ensures all API calls use MNR format regardless of input source
 */

/**
 * Normalizes user IDs from legacy MNR format to MNR format
 * @param {string} userId - User ID in any format (MNR182336064 or MNR182336064)
 * @returns {string} - Normalized MNR ID (MNR182336064)
 * 
 * Examples:
 *   normalizeAdminUserId('MNR182336064') → 'MNR182336064'
 *   normalizeAdminUserId('MNR182336064') → 'MNR182336064'
 *   normalizeAdminUserId('') → ''
 *   normalizeAdminUserId(null) → null
 */
function normalizeAdminUserId(userId) {
    if (!userId) {
        return userId;
    }
    
    const cleanedId = userId.toString().trim().toUpperCase();
    
    if (!cleanedId) {
        return cleanedId;
    }
    
    const mnrPattern = /^MNR(\d{7,9})$/;
    const match = cleanedId.match(mnrPattern);
    
    if (match) {
        const numericPart = match[1];
        return `MNR${numericPart}`;
    }
    
    return cleanedId;
}

/**
 * Validates if a user ID is in correct MNR format
 * @param {string} userId - User ID to validate
 * @returns {boolean} - True if valid MNR format
 * 
 * Examples:
 *   isValidMnrId('MNR182336064') → true
 *   isValidMnrId('MNR182336064') → false
 *   isValidMnrId('INVALID') → false
 */
function isValidMnrId(userId) {
    if (!userId) {
        return false;
    }
    
    const mnrPattern = /^MNR\d{7,9}$/;
    return mnrPattern.test(userId.trim());
}

/**
 * Normalizes and validates user ID, throws error if invalid
 * @param {string} userId - User ID to normalize and validate
 * @returns {string} - Normalized MNR ID
 * @throws {Error} - If ID format is invalid
 */
function normalizeAndValidateUserId(userId) {
    const normalized = normalizeAdminUserId(userId);
    
    if (!isValidMnrId(normalized)) {
        throw new Error(`Invalid user ID format: ${userId}. Expected format: MNR followed by 7-9 digits (e.g., MNR182336064)`);
    }
    
    return normalized;
}

/**
 * Batch normalizes an array of user IDs
 * @param {string[]} userIds - Array of user IDs to normalize
 * @returns {string[]} - Array of normalized MNR IDs
 */
function normalizeAdminUserIds(userIds) {
    if (!Array.isArray(userIds)) {
        return [];
    }
    
    return userIds.map(id => normalizeAdminUserId(id)).filter(id => id);
}

/**
 * Safely retrieves and normalizes user ID from sessionStorage
 * @param {string} key - sessionStorage key
 * @returns {string|null} - Normalized MNR ID or null
 */
function getAndNormalizeFromStorage(key) {
    try {
        const storedValue = sessionStorage.getItem(key);
        if (!storedValue) {
            return null;
        }
        
        const normalized = normalizeAdminUserId(storedValue);
        
        if (normalized !== storedValue) {
            sessionStorage.setItem(key, normalized);
        }
        
        return normalized;
    } catch (error) {
        console.error('Error accessing sessionStorage:', error);
        return null;
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        normalizeAdminUserId,
        isValidMnrId,
        normalizeAndValidateUserId,
        normalizeAdminUserIds,
        getAndNormalizeFromStorage
    };
}
