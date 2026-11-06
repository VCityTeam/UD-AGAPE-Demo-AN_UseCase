import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from photo_coordinates import (  # noqa: E402
    CoordinateError,
    scene_origin,
    transform_photos,
    viewer_position,
    wgs84_to_epsg3946,
)


ORIGIN = {"x": 1_846_182.445, "y": 5_175_904.754, "z": 165.953, "crs": "EPSG:3946"}


class PhotoCoordinateTests(unittest.TestCase):
    def test_projection_matches_epsg_reference(self):
        # Independent PROJ/cs2cs result for the viewer's published centre.
        easting, northing = wgs84_to_epsg3946(4.87959, 45.76816)
        self.assertAlmostEqual(easting, 1_846_181.30, places=2)
        self.assertAlmostEqual(northing, 5_175_958.25, places=2)

    def test_viewer_position_is_relative_to_scene_origin(self):
        self.assertEqual(viewer_position(4.87959, 45.76816, 170.953, ORIGIN), [-1.147, 53.499, 5.0])

    def test_missing_altitude_places_photo_at_origin_height(self):
        self.assertEqual(viewer_position(4.87959, 45.76816, None, ORIGIN)[2], 0.0)

    def test_plain_json_and_geojson_are_supported(self):
        photos = [
            {"id": "plain", "longitude": 4.87959, "latitude": 45.76816},
            {"type": "Feature", "properties": {"id": "geojson"},
             "geometry": {"type": "Point", "coordinates": [4.87959, 45.76816, 170.953]}},
        ]
        result = transform_photos(photos, ORIGIN)
        self.assertEqual(result[0]["id"], "plain")
        self.assertEqual(result[0]["position"], [-1.147, 53.499, 0.0])
        self.assertEqual(result[1], {"id": "geojson", "position": [-1.147, 53.499, 5.0]})

    def test_invalid_coordinates_identify_the_photo(self):
        with self.assertRaisesRegex(CoordinateError, "photo 0: longitude"):
            transform_photos([{"longitude": 181, "latitude": 45}], ORIGIN)

    def test_scene_origin_reads_generated_javascript(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scene.js"
            path.write_text(f"window.SCENE = {json.dumps({'origin': ORIGIN})};\n", encoding="utf-8")
            self.assertEqual(scene_origin(path), ORIGIN)


if __name__ == "__main__":
    unittest.main()
