import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "demonstrations"))

from commons_photos import COMMONS_API, WIKIDATA_API, category_location, discover  # noqa: E402

ORIGIN = {"x": 1_846_182.445, "y": 5_175_904.754, "z": 165.953, "crs": "EPSG:3946"}


class FakeApi:
    def __init__(self, category_coordinates=True):
        self.category_coordinates = category_coordinates

    def __call__(self, endpoint, parameters):
        if endpoint == WIKIDATA_API:
            return {"entities": {"Q42": {"claims": {"P625": [{"rank": "preferred", "mainsnak": {
                "datavalue": {"value": {"latitude": 45.77, "longitude": 4.88,
                                          "globe": "http://www.wikidata.org/entity/Q2"}}}}]}}}}
        if "titles" in parameters:
            page = {"title": parameters["titles"], "pageprops": {"wikibase_item": "Q42"}}
            if self.category_coordinates:
                page["coordinates"] = [{"lat": 45.768, "lon": 4.879, "globe": "earth"}]
            return {"query": {"pages": [page]}}
        return {"query": {"pages": [
            {"pageid": 1, "title": "File:Exact.jpg", "coordinates": [
                {"lat": 45.7681, "lon": 4.8781, "globe": "earth"}], "imageinfo": [{
                    "url": "https://upload.example/exact.jpg", "thumburl": "https://upload.example/thumb.jpg",
                    "descriptionurl": "https://commons.example/Exact", "extmetadata": {}}]},
            {"pageid": 2, "title": "File:Inferred.jpg", "imageinfo": [{
                "url": "https://upload.example/inferred.jpg", "descriptionurl": "https://commons.example/Inferred",
                "extmetadata": {"LicenseShortName": {"value": "CC BY-SA 4.0"}}}]},
        ]}}


class CommonsPhotoTests(unittest.TestCase):
    def test_file_coordinates_take_precedence_over_category(self):
        result = discover("Example", ORIGIN, 2, FakeApi())
        exact, inferred = result["photos"]
        self.assertEqual(exact["coordinateSource"]["type"], "commons-file")
        self.assertEqual(exact["coordinateSource"]["accuracy"], "camera")
        self.assertEqual(inferred["coordinateSource"]["type"], "commons-category")
        self.assertEqual(inferred["coordinateSource"]["accuracy"], "subject")
        self.assertEqual(inferred["licence"], "CC BY-SA 4.0")
        self.assertEqual(len(exact["position"]), 3)

    def test_category_falls_back_to_linked_wikidata_p625(self):
        location = category_location("Example", FakeApi(category_coordinates=False))
        self.assertEqual(location["type"], "wikidata")
        self.assertEqual(location["wikidata"], "Q42")
        self.assertEqual((location["latitude"], location["longitude"]), (45.77, 4.88))


if __name__ == "__main__":
    unittest.main()
