import re
import os
import unittest

def extract_coords_from_location_link(google_location):
    """Mirror of the backend coordinate extraction logic in community_services.py"""
    latitude, longitude = None, None
    if not google_location:
        return latitude, longitude

    loc_str = str(google_location).strip()
    plain_m = re.match(r'^[-+]?([1-8]?\d(?:\.\d+)?|90(?:\.0+)?)\s*,\s*[-+]?(180(?:\.0+)?|(?:(?:1[0-7]\d)|(?:[1-9]?\d))(?:\.\d+)?)$', loc_str)
    if plain_m:
        try:
            parts = loc_str.split(',')
            latitude = float(parts[0].strip())
            longitude = float(parts[1].strip())
        except Exception:
            pass
    if latitude is None or longitude is None:
        at_m = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', loc_str)
        if at_m:
            try:
                latitude = float(at_m.group(1))
                longitude = float(at_m.group(2))
            except Exception:
                pass
    if latitude is None or longitude is None:
        q_m = re.search(r'[?&](?:query|q|ll|destination|daddr)=(-?\d+\.\d+),(-?\d+\.\d+)', loc_str)
        if q_m:
            try:
                latitude = float(q_m.group(1))
                longitude = float(q_m.group(2))
            except Exception:
                pass
    if latitude is None or longitude is None:
        path_m = re.search(r'(?:search|place)/(-?\d+\.\d+),\+?(-?\d+\.\d+)', loc_str)
        if path_m:
            try:
                latitude = float(path_m.group(1))
                longitude = float(path_m.group(2))
            except Exception:
                pass
    return latitude, longitude


class TestGucLocationPaste(unittest.TestCase):

    def test_plain_coordinates_parsing(self):
        lat, lng = extract_coords_from_location_link("17.8300, 83.2000")
        self.assertAlmostEqual(lat, 17.8300, places=4)
        self.assertAlmostEqual(lng, 83.2000, places=4)

        lat, lng = extract_coords_from_location_link("17.8300,83.2000")
        self.assertAlmostEqual(lat, 17.8300, places=4)
        self.assertAlmostEqual(lng, 83.2000, places=4)

    def test_google_maps_at_coordinates(self):
        url = "https://www.google.com/maps/@17.831234,83.204567,17z?entry=ttu"
        lat, lng = extract_coords_from_location_link(url)
        self.assertAlmostEqual(lat, 17.831234, places=6)
        self.assertAlmostEqual(lng, 83.204567, places=6)

    def test_google_maps_query_and_search(self):
        url1 = "https://www.google.com/maps/search/?api=1&query=17.7289,83.3012"
        lat1, lng1 = extract_coords_from_location_link(url1)
        self.assertAlmostEqual(lat1, 17.7289, places=4)
        self.assertAlmostEqual(lng1, 83.3012, places=4)

        url2 = "https://maps.google.com/?q=17.7289,83.3012"
        lat2, lng2 = extract_coords_from_location_link(url2)
        self.assertAlmostEqual(lat2, 17.7289, places=4)
        self.assertAlmostEqual(lng2, 83.3012, places=4)

        url3 = "https://maps.google.com/?daddr=17.7289,83.3012"
        lat3, lng3 = extract_coords_from_location_link(url3)
        self.assertAlmostEqual(lat3, 17.7289, places=4)
        self.assertAlmostEqual(lng3, 83.3012, places=4)

    def test_google_maps_short_link_preservation(self):
        short_url = "https://maps.app.goo.gl/abCdEfGh123456"
        lat, lng = extract_coords_from_location_link(short_url)
        # Coordinates cannot be parsed from shortened URL without network redirect, so None is expected
        self.assertIsNone(lat)
        self.assertIsNone(lng)

    def test_frontend_guc_html_not_readonly(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        guc_path = os.path.join(base_dir, 'frontend', 'guc.html')
        self.assertTrue(os.path.exists(guc_path), f"File not found: {guc_path}")

        with open(guc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # google_location input must NOT be readonly
        self.assertIn('name="google_location"', content)
        # Confirm no readonly attribute on google_location input
        input_match = re.search(r'<input[^>]+name="google_location"[^>]*>', content)
        self.assertIsNotNone(input_match)
        self.assertNotIn('readonly', input_match.group(0))

        # Must have paste button, clear button, and functions
        self.assertIn('pasteLocationFromClipboard', content)
        self.assertIn('clearLocationInput', content)
        self.assertIn('parseGoogleMapsCoordinates', content)
        self.assertIn('handleLocationInput', content)
        self.assertIn('handleLocationPaste', content)
        self.assertIn('detectCurrentLocationDirectly', content)

    def test_frontend_community_landing_html_parity(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        comm_path = os.path.join(base_dir, 'frontend', 'community_landing.html')
        self.assertTrue(os.path.exists(comm_path), f"File not found: {comm_path}")

        with open(comm_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # google_location input must NOT be readonly
        self.assertIn('name="google_location"', content)
        input_match = re.search(r'<input[^>]+name="google_location"[^>]*>', content)
        self.assertIsNotNone(input_match)
        self.assertNotIn('readonly', input_match.group(0))

        # Must have paste button, clear button, and functions
        self.assertIn('pasteLocationFromClipboard', content)
        self.assertIn('clearLocationInput', content)
        self.assertIn('parseGoogleMapsCoordinates', content)
        self.assertIn('handleLocationInput', content)
        self.assertIn('handleLocationPaste', content)
        self.assertIn('detectCurrentLocationDirectly', content)


if __name__ == '__main__':
    unittest.main()
