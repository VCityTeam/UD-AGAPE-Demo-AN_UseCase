"""Convert geolocated photographs to positions in the 3D viewer.

The source coordinates are WGS 84 longitude/latitude (EPSG:4326).  The
viewer uses RGF93 / CC46 (EPSG:3946), expressed as metres relative to the
origin stored in ``data/viewer/scene.js``.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Mapping


# EPSG:3946: RGF93 v1 / CC46 (GRS 1980 ellipsoid, Lambert Conic Conformal 2SP)
_A = 6_378_137.0
_INV_F = 298.257222101
_LATITUDE_OF_ORIGIN = 46.0
_STANDARD_PARALLELS = (45.25, 46.75)
_CENTRAL_MERIDIAN = 3.0
_FALSE_EASTING = 1_700_000.0
_FALSE_NORTHING = 5_200_000.0


class CoordinateError(ValueError):
    """Raised when photo coordinates or viewer metadata are invalid."""


def _isometric_latitude(latitude: float, eccentricity: float) -> float:
    sine = math.sin(latitude)
    return math.log(
        math.tan(math.pi / 4 + latitude / 2)
        * ((1 - eccentricity * sine) / (1 + eccentricity * sine)) ** (eccentricity / 2)
    )


def wgs84_to_epsg3946(longitude: float, latitude: float) -> tuple[float, float]:
    """Project a WGS 84 position to EPSG:3946 easting and northing in metres.

    RGF93 and WGS 84 are coincident at the precision relevant to photographs,
    so EPSG specifies a null datum transformation for this viewer's CRS.
    """
    try:
        longitude, latitude = float(longitude), float(latitude)
    except (TypeError, ValueError) as error:
        raise CoordinateError("longitude and latitude must be numbers") from error
    if not math.isfinite(longitude) or not -180 <= longitude <= 180:
        raise CoordinateError("longitude must be between -180 and 180 degrees")
    if not math.isfinite(latitude) or not -90 < latitude < 90:
        raise CoordinateError("latitude must be between -90 and 90 degrees")

    flattening = 1 / _INV_F
    eccentricity = math.sqrt(2 * flattening - flattening * flattening)
    phi0, phi1, phi2 = map(math.radians, (_LATITUDE_OF_ORIGIN, *_STANDARD_PARALLELS))
    lam, lam0, phi = map(math.radians, (longitude, _CENTRAL_MERIDIAN, latitude))

    def radius(phi_value: float) -> float:
        return math.cos(phi_value) / math.sqrt(1 - eccentricity**2 * math.sin(phi_value) ** 2)

    l0 = _isometric_latitude(phi0, eccentricity)
    l1 = _isometric_latitude(phi1, eccentricity)
    l2 = _isometric_latitude(phi2, eccentricity)
    exponent = math.log(radius(phi1) / radius(phi2)) / (l2 - l1)
    constant = _A * radius(phi1) * math.exp(exponent * l1) / exponent
    rho0 = constant * math.exp(-exponent * l0)
    rho = constant * math.exp(-exponent * _isometric_latitude(phi, eccentricity))
    angle = exponent * (lam - lam0)
    return (
        _FALSE_EASTING + rho * math.sin(angle),
        _FALSE_NORTHING + rho0 - rho * math.cos(angle),
    )


def viewer_position(
    longitude: float,
    latitude: float,
    altitude: float | None,
    origin: Mapping[str, Any],
) -> list[float]:
    """Return ``[x, y, z]`` metres in the viewer's origin-relative frame."""
    if origin.get("crs") != "EPSG:3946":
        raise CoordinateError("viewer origin must use EPSG:3946")
    try:
        ox, oy, oz = (float(origin[name]) for name in ("x", "y", "z"))
    except (KeyError, TypeError, ValueError) as error:
        raise CoordinateError("viewer origin requires numeric x, y, and z values") from error
    easting, northing = wgs84_to_epsg3946(longitude, latitude)
    if altitude is None:
        z = 0.0
    else:
        try:
            z = float(altitude) - oz
        except (TypeError, ValueError) as error:
            raise CoordinateError("altitude must be a number or null") from error
        if not math.isfinite(z):
            raise CoordinateError("altitude must be finite")
    return [round(easting - ox, 3), round(northing - oy, 3), round(z, 3)]


def scene_origin(scene_path: str | Path) -> dict[str, Any]:
    """Read the origin object from the generated ``scene.js`` file."""
    text = Path(scene_path).read_text(encoding="utf-8")
    match = re.search(r"window\.SCENE\s*=\s*(\{.*\})\s*;\s*$", text, re.DOTALL)
    if not match:
        raise CoordinateError(f"could not find window.SCENE in {scene_path}")
    try:
        scene = json.loads(match.group(1))
        return scene["origin"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise CoordinateError(f"invalid scene data in {scene_path}") from error


def _coordinates(photo: Mapping[str, Any]) -> tuple[Any, Any, Any]:
    """Accept a plain photo object or a GeoJSON Point feature."""
    geometry = photo.get("geometry")
    if geometry is not None:
        if geometry.get("type") != "Point" or len(geometry.get("coordinates", [])) not in (2, 3):
            raise CoordinateError("GeoJSON photographs require a Point with 2 or 3 coordinates")
        coordinates = geometry["coordinates"]
        return coordinates[0], coordinates[1], coordinates[2] if len(coordinates) == 3 else None
    return photo.get("longitude"), photo.get("latitude"), photo.get("altitude")


def transform_photos(photos: Iterable[Mapping[str, Any]], origin: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Copy photo records and append their viewer-space ``position``."""
    transformed = []
    for index, photo in enumerate(photos):
        if not isinstance(photo, Mapping):
            raise CoordinateError(f"photo {index} must be an object")
        longitude, latitude, altitude = _coordinates(photo)
        try:
            position = viewer_position(longitude, latitude, altitude, origin)
        except CoordinateError as error:
            raise CoordinateError(f"photo {index}: {error}") from error
        item = dict(photo.get("properties", {})) if "geometry" in photo else dict(photo)
        item["position"] = position
        transformed.append(item)
    return transformed


def _photo_list(document: Any) -> list[Mapping[str, Any]]:
    if isinstance(document, list):
        return document
    if isinstance(document, dict) and document.get("type") == "FeatureCollection":
        return document.get("features", [])
    if isinstance(document, dict) and isinstance(document.get("photos"), list):
        return document["photos"]
    raise CoordinateError("input must be a photo array, a {photos: [...]} object, or a GeoJSON FeatureCollection")


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON or GeoJSON file containing geolocated photographs")
    parser.add_argument("output", type=Path, help="output JSON file for the viewer")
    parser.add_argument("--scene", type=Path, default=Path("data/viewer/scene.js"), help="generated viewer scene")
    args = parser.parse_args(arguments)
    document = json.loads(args.input.read_text(encoding="utf-8"))
    origin = scene_origin(args.scene)
    result = {"crs": "viewer-local", "origin": origin,
              "photos": transform_photos(_photo_list(document), origin)}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
