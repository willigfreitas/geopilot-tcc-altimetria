import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point

from tools.geopilot_geo_route import calculate_profile, create_profile_points


def test_profile_points_include_terminal_remainder() -> None:
    route = LineString([(0.0, 0.0), (4687.737694, 0.0)])
    points = create_profile_points(route, "EPSG:31983", 30.0)
    assert len(points) == 158
    assert points["distance_m"].iloc[0] == pytest.approx(0.0)
    assert points["distance_m"].iloc[-2] == pytest.approx(4680.0)
    assert points["distance_m"].iloc[-1] == pytest.approx(4687.737694)


def test_profile_points_include_exact_regular_endpoint_once() -> None:
    route = LineString([(0.0, 0.0), (90.0, 0.0)])
    points = create_profile_points(route, "EPSG:31983", 30.0)
    assert points["distance_m"].tolist() == [0.0, 30.0, 60.0, 90.0]


def test_profile_points_reject_nonpositive_spacing() -> None:
    route = LineString([(0.0, 0.0), (90.0, 0.0)])
    with pytest.raises(ValueError):
        create_profile_points(route, "EPSG:31983", 0.0)


def test_profile_calculates_ascent_and_descent() -> None:
    points = gpd.GeoDataFrame(
        {
            "sample_id": [1, 2, 3, 4],
            "distance_m": [0.0, 30.0, 60.0, 90.0],
            "elevation_m": [100.0, 103.0, 101.0, 106.0],
        },
        geometry=[Point(x, 0.0) for x in (0.0, 30.0, 60.0, 90.0)],
        crs="EPSG:31983",
    )
    profile = calculate_profile(points)
    assert profile["elevation_smooth_m"].tolist() == pytest.approx(
        [101.5, 101.333333, 103.333333, 103.5]
    )
    assert profile["positive_ascent_m"].sum() == pytest.approx(2.166667)
    assert profile["negative_descent_m"].sum() == pytest.approx(0.166667)
    assert profile["accumulated_ascent_m"].iloc[-1] == pytest.approx(2.166667)
    assert profile["accumulated_descent_m"].iloc[-1] == pytest.approx(0.166667)


def test_first_segment_has_zero_grade() -> None:
    points = gpd.GeoDataFrame(
        {
            "sample_id": [1, 2],
            "distance_m": [0.0, 30.0],
            "elevation_m": [100.0, 103.0],
        },
        geometry=[Point(0.0, 0.0), Point(30.0, 0.0)],
        crs="EPSG:31983",
    )
    profile = calculate_profile(points)
    assert profile["grade_percent"].iloc[0] == pytest.approx(0.0)
