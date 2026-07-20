"""
Journey Validation Service
DC Protocol: Complete route validation for journey approval
WVV: Speed anomaly, teleportation, continuity validation

Created: December 1, 2025
Purpose: Validate journey routes before approval per WVV and DC protocols
"""
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import math


class JourneyValidationService:
    """
    DC_JOURNEY_VALIDATION_001: Comprehensive route validation service
    Validates journeys before approval to prevent fraudulent reimbursement claims
    """
    
    # WVV Protocol: Maximum speeds by transport mode (km/h)
    MAX_SPEEDS = {
        'bike': 80,
        'electric_bike': 45,
        'car': 180,
        'cart': 40,
        'local_transport': 100,
        'others': 60
    }
    
    # WVV Protocol: Minimum track points for valid journey
    # DC_TRACK_POINT_001: 5 points minimum for route verification
    MIN_TRACK_POINTS = 5
    
    # WVV Protocol: Maximum GPS accuracy tolerance (meters)
    MAX_GPS_ACCURACY = 100
    
    # WVV Protocol: Teleportation detection - max distance in seconds
    # If distance/time ratio exceeds this, it's teleportation
    TELEPORTATION_SPEED_THRESHOLD = 200  # km/h - no transport goes this fast
    
    # WVV Protocol: Minimum time between points to detect anomalies (seconds)
    MIN_POINT_INTERVAL = 5
    
    @classmethod
    def validate_journey_for_approval(
        cls,
        journey_data: Dict,
        track_points: List[Dict]
    ) -> Dict:
        """
        DC_JOURNEY_VALIDATION_002: Main validation entry point
        
        Returns:
        {
            "is_valid": bool,
            "validation_score": int (0-100),
            "warnings": List[str],
            "errors": List[str],
            "critical_failures": List[str],  # Hard blockers
            "validations": {
                "track_points": {...},
                "speed": {...},
                "teleportation": {...},
                "continuity": {...},
                "photo": {...},
                "gps_accuracy": {...}
            }
        }
        """
        warnings = []
        errors = []
        critical_failures = []  # DC_CRITICAL_VALIDATION_001: Hard blockers
        validations = {}
        
        # 1. Track Points Validation - CRITICAL if insufficient
        tp_result = cls.validate_track_points(track_points)
        validations['track_points'] = tp_result
        if not tp_result['is_valid']:
            errors.extend(tp_result.get('errors', []))
            if tp_result.get('is_critical'):
                critical_failures.append("CRITICAL: Insufficient GPS track points for route verification")
        warnings.extend(tp_result.get('warnings', []))
        
        # 2. Speed Anomaly Detection (with fallback calculation)
        speed_result = cls.validate_speed_anomalies(
            track_points, 
            journey_data.get('transport_mode', 'others')
        )
        validations['speed'] = speed_result
        if not speed_result['is_valid']:
            errors.extend(speed_result.get('errors', []))
            if speed_result.get('is_critical'):
                critical_failures.append("CRITICAL: Speed anomaly detected - impossible speeds for transport mode")
        warnings.extend(speed_result.get('warnings', []))
        
        # 3. Teleportation Detection - CRITICAL FAILURE
        teleport_result = cls.detect_teleportation(track_points)
        validations['teleportation'] = teleport_result
        if not teleport_result['is_valid']:
            errors.extend(teleport_result.get('errors', []))
            critical_failures.append("CRITICAL: Teleportation detected - impossible position jumps")
        warnings.extend(teleport_result.get('warnings', []))
        
        # 4. Route Continuity Validation
        continuity_result = cls.validate_route_continuity(track_points)
        validations['continuity'] = continuity_result
        if not continuity_result['is_valid']:
            errors.extend(continuity_result.get('errors', []))
        warnings.extend(continuity_result.get('warnings', []))
        
        # 5. Photo Verification
        photo_result = cls.validate_photo(journey_data)
        validations['photo'] = photo_result
        if not photo_result['is_valid']:
            warnings.append("No photo uploaded - optional for reimbursement but recommended")
        
        # 6. GPS Accuracy Validation - CRITICAL if >50% poor
        accuracy_result = cls.validate_gps_accuracy(track_points)
        validations['gps_accuracy'] = accuracy_result
        if not accuracy_result['is_valid']:
            errors.extend(accuracy_result.get('errors', []))
            if accuracy_result.get('is_critical'):
                critical_failures.append("CRITICAL: GPS accuracy severely degraded - over 50% points exceed WVV limit")
        warnings.extend(accuracy_result.get('warnings', []))
        
        # Calculate validation score (0-100)
        score = cls.calculate_validation_score(validations)
        
        # DC_CRITICAL_VALIDATION_002: Hard blocker - any critical failure forces score to 0
        if critical_failures:
            score = 0
        
        # Final result - MUST have no critical failures and score >= 60
        is_valid = len(critical_failures) == 0 and len(errors) == 0 and score >= 60
        
        # DC_RECOMMENDATION_LOGIC_001: Clear recommendation based on score and critical failures
        if critical_failures:
            recommendation = "REJECT"
        elif is_valid:
            recommendation = "APPROVE"
        elif score >= 40:
            recommendation = "REVIEW"
        else:
            recommendation = "REJECT"
        
        return {
            "is_valid": is_valid,
            "validation_score": score,
            "warnings": warnings,
            "errors": errors,
            "critical_failures": critical_failures,
            "has_critical_failures": len(critical_failures) > 0,
            "validations": validations,
            "recommendation": recommendation
        }
    
    @classmethod
    def validate_track_points(cls, track_points: List[Dict]) -> Dict:
        """
        DC_TRACK_POINT_VALIDATION_001: Validate minimum track points
        DC_CRITICAL_TRACK_001: Insufficient track points is a critical failure
        """
        count = len(track_points)
        
        if count < cls.MIN_TRACK_POINTS:
            return {
                "is_valid": False,
                "is_critical": True,  # DC_CRITICAL_TRACK_001: Hard blocker
                "count": count,
                "minimum_required": cls.MIN_TRACK_POINTS,
                "errors": [f"CRITICAL: Insufficient track points: {count} < {cls.MIN_TRACK_POINTS} required"],
                "warnings": []
            }
        
        warnings = []
        if count < 10:
            warnings.append(f"Low track point count: {count} points. Route may be sparse.")
        
        return {
            "is_valid": True,
            "is_critical": False,
            "count": count,
            "minimum_required": cls.MIN_TRACK_POINTS,
            "errors": [],
            "warnings": warnings
        }
    
    @classmethod
    def validate_speed_anomalies(
        cls, 
        track_points: List[Dict], 
        transport_mode: str
    ) -> Dict:
        """
        DC_SPEED_VALIDATION_001: Detect impossible speeds for transport mode
        WVV_SPEED_FALLBACK_001: Calculate speed from coordinates when device speed missing
        """
        max_speed = cls.MAX_SPEEDS.get(transport_mode, 60)
        anomalies = []
        calculated_speeds = []
        
        for i, tp in enumerate(track_points):
            speed = tp.get('speed_kmh')
            
            # WVV_SPEED_FALLBACK_001: Calculate speed from distance/time if device speed missing
            if speed is None and i > 0:
                prev = track_points[i - 1]
                prev_time = cls._parse_timestamp(prev.get('timestamp'))
                curr_time = cls._parse_timestamp(tp.get('timestamp'))
                
                if prev_time and curr_time:
                    time_diff_seconds = (curr_time - prev_time).total_seconds()
                    if time_diff_seconds >= cls.MIN_POINT_INTERVAL:
                        distance_km = cls.haversine_distance(
                            prev.get('latitude'), prev.get('longitude'),
                            tp.get('latitude'), tp.get('longitude')
                        )
                        speed = (distance_km / time_diff_seconds) * 3600
                        calculated_speeds.append({
                            "point_index": i,
                            "calculated_speed_kmh": round(speed, 1),
                            "source": "distance_time_calculation"
                        })
            
            if speed and speed > max_speed:
                anomalies.append({
                    "point_index": i,
                    "speed_kmh": round(speed, 1),
                    "max_allowed": max_speed,
                    "timestamp": tp.get('timestamp'),
                    "calculated": speed not in [tp.get('speed_kmh')]
                })
        
        # DC_CRITICAL_SPEED_001: Mark as critical if many anomalies
        is_critical = len(anomalies) >= 3 or any(a['speed_kmh'] > max_speed * 2 for a in anomalies)
        
        if anomalies:
            return {
                "is_valid": False,
                "is_critical": is_critical,
                "transport_mode": transport_mode,
                "max_allowed_speed": max_speed,
                "anomaly_count": len(anomalies),
                "anomalies": anomalies[:5],
                "calculated_speeds_count": len(calculated_speeds),
                "errors": [f"Speed anomaly detected: {len(anomalies)} points exceed {max_speed} km/h for {transport_mode}"],
                "warnings": []
            }
        
        return {
            "is_valid": True,
            "is_critical": False,
            "transport_mode": transport_mode,
            "max_allowed_speed": max_speed,
            "anomaly_count": 0,
            "calculated_speeds_count": len(calculated_speeds),
            "errors": [],
            "warnings": []
        }
    
    @classmethod
    def detect_teleportation(cls, track_points: List[Dict]) -> Dict:
        """
        DC_TELEPORTATION_DETECTION_001: Detect impossible position jumps
        WVV_TIMESTAMP_VALIDATION_001: Enforce monotonic timestamps
        """
        teleportations = []
        timestamp_issues = []
        last_valid_time = None
        
        for i in range(1, len(track_points)):
            prev = track_points[i - 1]
            curr = track_points[i]
            
            # Calculate distance
            distance_km = cls.haversine_distance(
                prev.get('latitude'), prev.get('longitude'),
                curr.get('latitude'), curr.get('longitude')
            )
            
            # Calculate time difference with robust handling
            prev_time = cls._parse_timestamp(prev.get('timestamp'))
            curr_time = cls._parse_timestamp(curr.get('timestamp'))
            
            if prev_time and curr_time:
                time_diff_seconds = (curr_time - prev_time).total_seconds()
                
                # WVV_TIMESTAMP_VALIDATION_001: Check for non-monotonic timestamps
                if time_diff_seconds < 0:
                    timestamp_issues.append({
                        "point_index": i,
                        "issue": "non_monotonic_timestamp",
                        "time_diff_seconds": time_diff_seconds
                    })
                    continue  # Skip this point for teleportation check
                
                # DC_ZERO_INTERVAL_HANDLING_001: Handle zero/very small intervals
                if time_diff_seconds < cls.MIN_POINT_INTERVAL:
                    # If significant distance in very short time, flag as suspicious
                    if distance_km > 0.1:  # More than 100m in < 5 seconds
                        teleportations.append({
                            "from_point": i - 1,
                            "to_point": i,
                            "distance_km": round(distance_km, 2),
                            "time_seconds": time_diff_seconds,
                            "calculated_speed_kmh": float('inf') if time_diff_seconds == 0 else round((distance_km / time_diff_seconds) * 3600, 1),
                            "from_coords": [prev.get('latitude'), prev.get('longitude')],
                            "to_coords": [curr.get('latitude'), curr.get('longitude')],
                            "issue": "zero_time_large_distance"
                        })
                    continue  # Skip normal speed calculation for very short intervals
                
                # Normal teleportation check
                speed_kmh = (distance_km / time_diff_seconds) * 3600
                
                if speed_kmh > cls.TELEPORTATION_SPEED_THRESHOLD:
                    teleportations.append({
                        "from_point": i - 1,
                        "to_point": i,
                        "distance_km": round(distance_km, 2),
                        "time_seconds": round(time_diff_seconds, 1),
                        "calculated_speed_kmh": round(speed_kmh, 1),
                        "from_coords": [prev.get('latitude'), prev.get('longitude')],
                        "to_coords": [curr.get('latitude'), curr.get('longitude')],
                        "issue": "impossible_speed"
                    })
        
        warnings = []
        if timestamp_issues:
            warnings.append(f"{len(timestamp_issues)} points have non-monotonic timestamps")
        
        if teleportations:
            return {
                "is_valid": False,
                "teleportation_count": len(teleportations),
                "teleportations": teleportations[:3],
                "timestamp_issues": len(timestamp_issues),
                "errors": [f"Teleportation detected: {len(teleportations)} impossible position jumps"],
                "warnings": warnings
            }
        
        return {
            "is_valid": True,
            "teleportation_count": 0,
            "timestamp_issues": len(timestamp_issues),
            "errors": [],
            "warnings": warnings
        }
    
    @classmethod
    def validate_route_continuity(cls, track_points: List[Dict]) -> Dict:
        """
        DC_ROUTE_CONTINUITY_001: Validate route follows logical path
        """
        if len(track_points) < 2:
            return {
                "is_valid": True,
                "continuity_score": 100,
                "gaps": [],
                "errors": [],
                "warnings": ["Too few points for continuity analysis"]
            }
        
        gaps = []
        total_distance = 0
        
        for i in range(1, len(track_points)):
            prev = track_points[i - 1]
            curr = track_points[i]
            
            distance_km = cls.haversine_distance(
                prev.get('latitude'), prev.get('longitude'),
                curr.get('latitude'), curr.get('longitude')
            )
            
            total_distance += distance_km
            
            # Gap detection: More than 5km between consecutive points
            if distance_km > 5:
                gaps.append({
                    "from_point": i - 1,
                    "to_point": i,
                    "gap_km": round(distance_km, 2)
                })
        
        warnings = []
        if gaps:
            warnings.append(f"Route has {len(gaps)} gaps > 5km. May indicate GPS interruption.")
        
        # Continuity score (100 - penalty for gaps)
        continuity_score = max(0, 100 - (len(gaps) * 10))
        
        return {
            "is_valid": True,  # Gaps are warnings, not errors
            "continuity_score": continuity_score,
            "total_distance_km": round(total_distance, 2),
            "gap_count": len(gaps),
            "gaps": gaps[:5],  # First 5 gaps
            "errors": [],
            "warnings": warnings
        }
    
    @classmethod
    def validate_photo(cls, journey_data: Dict) -> Dict:
        """
        DC_PHOTO_VALIDATION_001: Validate photo upload status
        """
        photo_path = journey_data.get('photo_path')
        
        return {
            "is_valid": bool(photo_path),
            "has_photo": bool(photo_path),
            "photo_path": photo_path,
            "errors": [],
            "warnings": [] if photo_path else ["No photo uploaded"]
        }
    
    @classmethod
    def validate_gps_accuracy(cls, track_points: List[Dict]) -> Dict:
        """
        DC_GPS_ACCURACY_001: Validate GPS accuracy within WVV limits
        DC_CRITICAL_GPS_001: Mark as critical if >50% points exceed accuracy threshold
        """
        if not track_points:
            return {
                "is_valid": False,
                "is_critical": False,
                "poor_accuracy_count": 0,
                "total_points": 0,
                "percentage_poor": 0,
                "errors": ["No track points to validate"],
                "warnings": []
            }
        
        poor_accuracy_points = []
        
        for i, tp in enumerate(track_points):
            accuracy = tp.get('accuracy')
            if accuracy and accuracy > cls.MAX_GPS_ACCURACY:
                poor_accuracy_points.append({
                    "point_index": i,
                    "accuracy_m": accuracy,
                    "max_allowed": cls.MAX_GPS_ACCURACY
                })
        
        percentage_poor = round(len(poor_accuracy_points) / len(track_points) * 100, 1)
        
        # DC_CRITICAL_GPS_001: >50% poor accuracy is a critical failure
        is_critical = percentage_poor > 50
        
        if percentage_poor > 30:  # More than 30% poor accuracy
            return {
                "is_valid": False,
                "is_critical": is_critical,
                "poor_accuracy_count": len(poor_accuracy_points),
                "total_points": len(track_points),
                "percentage_poor": percentage_poor,
                "errors": [f"GPS accuracy issue: {len(poor_accuracy_points)} points ({percentage_poor}%) exceed {cls.MAX_GPS_ACCURACY}m"],
                "warnings": []
            }
        
        warnings = []
        if poor_accuracy_points:
            warnings.append(f"{len(poor_accuracy_points)} points had accuracy > {cls.MAX_GPS_ACCURACY}m")
        
        return {
            "is_valid": True,
            "is_critical": False,
            "poor_accuracy_count": len(poor_accuracy_points),
            "total_points": len(track_points),
            "percentage_poor": percentage_poor,
            "errors": [],
            "warnings": warnings
        }
    
    @classmethod
    def calculate_validation_score(cls, validations: Dict) -> int:
        """
        DC_VALIDATION_SCORE_001: Calculate overall journey validity score
        """
        score = 100
        
        # Deductions
        if not validations.get('track_points', {}).get('is_valid'):
            score -= 30
        elif validations.get('track_points', {}).get('count', 0) < 10:
            score -= 10
        
        if not validations.get('speed', {}).get('is_valid'):
            score -= 25
        
        if not validations.get('teleportation', {}).get('is_valid'):
            score -= 40  # Critical
        
        if not validations.get('continuity', {}).get('is_valid'):
            score -= 15
        else:
            continuity_score = validations.get('continuity', {}).get('continuity_score', 100)
            score -= (100 - continuity_score) // 5
        
        if not validations.get('photo', {}).get('is_valid'):
            score -= 5  # Minor deduction
        
        if not validations.get('gps_accuracy', {}).get('is_valid'):
            score -= 20
        
        return max(0, min(100, score))
    
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two GPS coordinates in kilometers
        DC_GPS_MATH_001: Handles legitimate 0.0 coordinates (equator/prime meridian)
        """
        # DC_GPS_MATH_001: Check for None explicitly, not truthiness (0.0 is valid!)
        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            return 0.0
            
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return round(R * c, 4)
    
    @staticmethod
    def _parse_timestamp(ts) -> Optional[datetime]:
        """Parse timestamp from various formats"""
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except:
                return None
        return None
