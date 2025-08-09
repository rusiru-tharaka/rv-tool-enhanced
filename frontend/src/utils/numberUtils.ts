/**
 * Utility functions for safe number handling and rendering
 * Prevents NaN errors in React components
 */

/**
 * Safely renders a number value, handling null, undefined, and NaN cases
 * @param value - The value to render
 * @param defaultValue - Default value to return if input is invalid
 * @param precision - Number of decimal places (default: 2)
 * @returns Safe string or number representation
 */
export const safeNumber = (
  value: any, 
  defaultValue: string | number = 0, 
  precision: number = 2
): string | number => {
  // Handle null, undefined, or empty string
  if (value === null || value === undefined || value === '') {
    return defaultValue;
  }

  // Convert to number if it's a string
  const numValue = typeof value === 'string' ? parseFloat(value) : value;

  // Handle NaN or invalid numbers
  if (isNaN(numValue) || !isFinite(numValue)) {
    return defaultValue;
  }

  // Return rounded number for valid numeric values
  return typeof numValue === 'number' ? 
    Math.round(numValue * Math.pow(10, precision)) / Math.pow(10, precision) : 
    numValue;
};

/**
 * Safely renders a percentage value
 * @param value - The decimal value (e.g., 0.25 for 25%)
 * @param defaultValue - Default value to return if input is invalid
 * @returns Formatted percentage string
 */
export const safePercentage = (
  value: any, 
  defaultValue: string = '0%'
): string => {
  const numValue = safeNumber(value, 0);
  
  if (typeof numValue === 'number') {
    return `${Math.round(numValue * 100)}%`;
  }
  
  return defaultValue;
};

/**
 * Safely renders a currency value
 * @param value - The numeric value
 * @param currency - Currency symbol (default: '$')
 * @param defaultValue - Default value to return if input is invalid
 * @returns Formatted currency string
 */
export const safeCurrency = (
  value: any, 
  currency: string = '$', 
  defaultValue: string = '$0'
): string => {
  const numValue = safeNumber(value, 0);
  
  if (typeof numValue === 'number') {
    return `${currency}${numValue.toLocaleString()}`;
  }
  
  return defaultValue;
};

/**
 * Safely renders a count or integer value
 * @param value - The value to render
 * @param defaultValue - Default value to return if input is invalid
 * @returns Safe integer representation
 */
export const safeCount = (
  value: any, 
  defaultValue: number = 0
): number => {
  const numValue = safeNumber(value, defaultValue, 0);
  return typeof numValue === 'number' ? Math.max(0, Math.floor(numValue)) : defaultValue;
};

/**
 * Safely renders array length
 * @param array - The array to get length from
 * @param defaultValue - Default value to return if array is invalid
 * @returns Safe array length
 */
export const safeArrayLength = (
  array: any[] | null | undefined, 
  defaultValue: number = 0
): number => {
  return Array.isArray(array) ? array.length : defaultValue;
};

/**
 * Checks if a value is a valid number
 * @param value - The value to check
 * @returns True if value is a valid number
 */
export const isValidNumber = (value: any): boolean => {
  return typeof value === 'number' && !isNaN(value) && isFinite(value);
};

/**
 * Safely formats a duration in months
 * @param months - Number of months
 * @param defaultValue - Default value to return if input is invalid
 * @returns Formatted duration string
 */
export const safeDuration = (
  months: any, 
  defaultValue: string = 'TBD'
): string => {
  const numMonths = safeNumber(months, null);
  
  if (typeof numMonths === 'number' && numMonths > 0) {
    if (numMonths < 12) {
      return `${Math.round(numMonths)} month${numMonths !== 1 ? 's' : ''}`;
    } else {
      const years = Math.floor(numMonths / 12);
      const remainingMonths = Math.round(numMonths % 12);
      
      if (remainingMonths === 0) {
        return `${years} year${years !== 1 ? 's' : ''}`;
      } else {
        return `${years}y ${remainingMonths}m`;
      }
    }
  }
  
  return defaultValue;
};

/**
 * Format large numbers with appropriate suffixes (K, M, B)
 * @param value - The numeric value
 * @param defaultValue - Default value to return if input is invalid
 * @returns Formatted number string
 */
export const formatLargeNumber = (
  value: any,
  defaultValue: string = '0'
): string => {
  const numValue = safeNumber(value, 0);
  
  if (typeof numValue !== 'number') {
    return defaultValue;
  }
  
  if (numValue >= 1000000000) {
    return `${(numValue / 1000000000).toFixed(1)}B`;
  } else if (numValue >= 1000000) {
    return `${(numValue / 1000000).toFixed(1)}M`;
  } else if (numValue >= 1000) {
    return `${(numValue / 1000).toFixed(1)}K`;
  } else {
    return numValue.toString();
  }
};

/**
 * Calculate percentage change between two values
 * @param oldValue - The original value
 * @param newValue - The new value
 * @param defaultValue - Default value to return if calculation fails
 * @returns Formatted percentage change string
 */
export const calculatePercentageChange = (
  oldValue: any,
  newValue: any,
  defaultValue: string = '0%'
): string => {
  const oldNum = safeNumber(oldValue, null);
  const newNum = safeNumber(newValue, null);
  
  if (typeof oldNum === 'number' && typeof newNum === 'number' && oldNum !== 0) {
    const change = ((newNum - oldNum) / oldNum) * 100;
    const sign = change > 0 ? '+' : '';
    return `${sign}${change.toFixed(1)}%`;
  }
  
  return defaultValue;
};
