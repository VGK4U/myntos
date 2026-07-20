const EARTH_RADIUS_M = 6371000;

export function toRadians(degrees: number): number {
  return degrees * (Math.PI / 180);
}

export function calculateHaversineDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const dLat = toRadians(lat2 - lat1);
  const dLon = toRadians(lon2 - lon1);
  
  const a = 
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  
  return EARTH_RADIUS_M * c;
}

export function calculateSpeed(
  lat1: number,
  lon1: number,
  timestamp1: string,
  lat2: number,
  lon2: number,
  timestamp2: string
): number | null {
  const distance_m = calculateHaversineDistance(lat1, lon1, lat2, lon2);
  
  const time1 = new Date(timestamp1).getTime();
  const time2 = new Date(timestamp2).getTime();
  const time_diff_hours = (time2 - time1) / (1000 * 60 * 60);
  
  if (time_diff_hours <= 0) return null;
  
  const distance_km = distance_m / 1000;
  return distance_km / time_diff_hours;
}

export function metersToKilometers(meters: number): number {
  return meters / 1000;
}

export function kilometersToMeters(kilometers: number): number {
  return kilometers * 1000;
}
