"""Automação acadêmica do perfil altimétrico de uma rota."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

import geopandas as gpd
import numpy as np
import rasterio
from shapely.geometry import LineString
from shapely.ops import linemerge


@dataclass(frozen=True)
class GeoRouteConfig:
    routes: Path
    dem: Path
    output: Path
    crs: str
    sample_spacing: float


def positive_number(value: str) -> float:
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("O valor deve ser maior que zero.")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Processa uma rota e um MDE para gerar indicadores altimétricos."
        )
    )
    parser.add_argument("--routes", type=Path, required=True)
    parser.add_argument("--dem", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--crs", default="EPSG:31983")
    parser.add_argument(
        "--sample-spacing",
        type=positive_number,
        default=30.0,
        help="Espaçamento nominal entre amostras, em metros.",
    )
    return parser


def build_config(namespace: argparse.Namespace) -> GeoRouteConfig:
    return GeoRouteConfig(
        routes=namespace.routes.expanduser().resolve(),
        dem=namespace.dem.expanduser().resolve(),
        output=namespace.output.expanduser().resolve(),
        crs=namespace.crs,
        sample_spacing=namespace.sample_spacing,
    )


def validate_config(config: GeoRouteConfig) -> None:
    errors: list[str] = []
    if not config.routes.is_file():
        errors.append(f"Arquivo de rotas não encontrado: {config.routes}")
    if not config.dem.is_file():
        errors.append(f"MDE não encontrado: {config.dem}")
    if not config.crs.upper().startswith("EPSG:"):
        errors.append(f"SRC inválido: {config.crs}. Use o formato EPSG:31983.")
    if errors:
        raise ValueError("\n".join(errors))


def save_parameters(config: GeoRouteConfig) -> Path:
    config.output.mkdir(parents=True, exist_ok=True)
    destination = config.output / "parametros_execucao.json"
    data = asdict(config)
    for field in ("routes", "dem", "output"):
        data[field] = str(data[field])
    data["executed_at"] = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    data["status"] = "processamento_pendente"
    destination.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return destination


def load_route(config: GeoRouteConfig) -> tuple[LineString, object]:
    routes = gpd.read_file(config.routes)
    if routes.empty:
        raise ValueError("O arquivo vetorial não contém rotas.")
    if routes.crs is None:
        raise ValueError("O arquivo de rotas não possui SRC definido.")

    routes = routes[routes.geometry.notna() & ~routes.geometry.is_empty].copy()
    if routes.empty:
        raise ValueError("Nenhuma geometria válida foi encontrada.")

    invalid_types = set(routes.geometry.geom_type) - {
        "LineString",
        "MultiLineString",
    }
    if invalid_types:
        raise ValueError(
            "A camada deve conter somente linhas. "
            f"Tipos encontrados: {sorted(invalid_types)}"
        )

    routes = routes.to_crs(config.crs)
    united = routes.geometry.union_all()
    route = united if united.geom_type == "LineString" else linemerge(united)
    if route.geom_type != "LineString":
        raise ValueError(
            "Não foi possível consolidar as feições em uma única "
            "LineString contínua."
        )
    if route.length <= 0:
        raise ValueError("A rota possui comprimento igual a zero.")
    return route, routes.crs


def create_profile_points(
    route: LineString,
    crs: object,
    spacing_m: float,
) -> gpd.GeoDataFrame:
    """Cria pontos regulares e inclui o ponto terminal exato."""

    if spacing_m <= 0:
        raise ValueError("O espaçamento deve ser maior que zero.")

    route_length = float(route.length)
    regular_segment_count = math.floor(route_length / spacing_m)
    distances = [
        float(index * spacing_m)
        for index in range(regular_segment_count + 1)
    ]
    if not math.isclose(
        distances[-1], route_length, rel_tol=0.0, abs_tol=0.001
    ):
        distances.append(route_length)

    return gpd.GeoDataFrame(
        {
            "sample_id": range(1, len(distances) + 1),
            "distance_m": distances,
        },
        geometry=[route.interpolate(distance) for distance in distances],
        crs=crs,
    )


def sample_dem(
    points: gpd.GeoDataFrame,
    dem_path: Path,
) -> tuple[gpd.GeoDataFrame, dict[str, object]]:
    with rasterio.open(dem_path) as dem:
        if dem.crs is None:
            raise ValueError("O MDE não possui SRC definido.")
        sampling_points = points.to_crs(dem.crs)
        coordinates = [(geometry.x, geometry.y) for geometry in sampling_points.geometry]
        elevations = []
        for sampled_value in dem.sample(coordinates, indexes=1, masked=True):
            value = sampled_value[0]
            elevations.append(
                float("nan") if np.ma.is_masked(value) else float(value)
            )
        metadata = {
            "crs": str(dem.crs),
            "resolution_x": float(dem.res[0]),
            "resolution_y": float(dem.res[1]),
            "nodata": dem.nodata,
            "bounds": [float(value) for value in dem.bounds],
        }

    result = points.copy()
    result["elevation_m"] = elevations
    invalid_count = int(result["elevation_m"].isna().sum())
    if invalid_count:
        raise ValueError(
            f"O MDE retornou {invalid_count} amostra(s) sem elevação."
        )
    return result, metadata


def calculate_profile(points: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    result = points.copy()
    result["elevation_smooth_m"] = (
        result["elevation_m"]
        .rolling(window=3, center=True, min_periods=1)
        .mean()
    )
    result["segment_distance_m"] = result["distance_m"].diff().fillna(0.0)
    result["elevation_change_m"] = (
        result["elevation_smooth_m"].diff().fillna(0.0)
    )
    denominator = result["segment_distance_m"].replace(0.0, np.nan)
    result["grade_percent"] = (
        result["elevation_change_m"]
        .div(denominator)
        .mul(100.0)
        .fillna(0.0)
    )
    result["positive_ascent_m"] = result["elevation_change_m"].clip(lower=0.0)
    result["negative_descent_m"] = (
        result["elevation_change_m"].clip(upper=0.0).abs()
    )
    result["accumulated_ascent_m"] = result["positive_ascent_m"].cumsum()
    result["accumulated_descent_m"] = result["negative_descent_m"].cumsum()
    result["x"] = result.geometry.x
    result["y"] = result.geometry.y
    return result


def export_results(
    config: GeoRouteConfig,
    profile: gpd.GeoDataFrame,
    dem_metadata: dict[str, object],
    route_length_m: float,
) -> tuple[Path, Path, Path, dict[str, object]]:
    config.output.mkdir(parents=True, exist_ok=True)
    csv_path = config.output / "perfil_altimetrico.csv"
    gpkg_path = config.output / "pontos_perfil.gpkg"
    summary_path = config.output / "resumo_rota.json"

    csv_columns = [
        "sample_id", "distance_m", "elevation_m", "elevation_smooth_m",
        "segment_distance_m", "elevation_change_m", "grade_percent",
        "positive_ascent_m", "accumulated_ascent_m", "negative_descent_m",
        "accumulated_descent_m", "x", "y",
    ]
    profile[csv_columns].to_csv(
        csv_path, index=False, encoding="utf-8-sig", float_format="%.6f"
    )
    profile.to_file(gpkg_path, layer="perfil_altimetrico", driver="GPKG")

    sampled_distance_m = float(profile["distance_m"].iloc[-1])
    valid_grades = profile.loc[
        profile["segment_distance_m"] > 0, "grade_percent"
    ]
    summary: dict[str, object] = {
        "route_file": str(config.routes),
        "dem_file": str(config.dem),
        "calculation_crs": config.crs,
        "sample_spacing_m": config.sample_spacing,
        "sample_count": len(profile),
        "distance_km": route_length_m / 1000.0,
        "route_length_m": route_length_m,
        "sampled_distance_m": sampled_distance_m,
        "terminal_remainder_m": route_length_m - sampled_distance_m,
        "initial_elevation_m": float(profile["elevation_smooth_m"].iloc[0]),
        "final_elevation_m": float(profile["elevation_smooth_m"].iloc[-1]),
        "net_elevation_change_m": float(
            profile["elevation_smooth_m"].iloc[-1]
            - profile["elevation_smooth_m"].iloc[0]
        ),
        "accumulated_ascent_m": float(profile["positive_ascent_m"].sum()),
        "accumulated_descent_m": float(profile["negative_descent_m"].sum()),
        "mean_absolute_grade_percent": float(valid_grades.abs().mean()),
        "maximum_uphill_grade_percent": float(profile["grade_percent"].max()),
        "maximum_downhill_grade_percent": float(profile["grade_percent"].min()),
        "dem_metadata": dem_metadata,
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return csv_path, gpkg_path, summary_path, summary


def run(config: GeoRouteConfig) -> int:
    validate_config(config)
    parameters_file = save_parameters(config)
    print("GeoPilot — automação altimétrica do TCC")
    route, route_crs = load_route(config)
    points = create_profile_points(route, route_crs, config.sample_spacing)
    profile, dem_metadata = sample_dem(points, config.dem)
    profile = calculate_profile(profile)
    csv_path, gpkg_path, summary_path, summary = export_results(
        config, profile, dem_metadata, float(route.length)
    )

    parameters = json.loads(parameters_file.read_text(encoding="utf-8"))
    parameters["status"] = "processamento_concluido"
    parameters["outputs"] = {
        "profile_csv": str(csv_path),
        "profile_gpkg": str(gpkg_path),
        "summary_json": str(summary_path),
    }
    parameters_file.write_text(
        json.dumps(parameters, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Comprimento vetorial: {summary['distance_km']:.3f} km")
    print(f"Amostras: {len(profile)}")
    print(f"Subida acumulada: {summary['accumulated_ascent_m']:.2f} m")
    print(f"Descida acumulada: {summary['accumulated_descent_m']:.2f} m")
    print(f"Perfil CSV: {csv_path}")
    print(f"Pontos GPKG: {gpkg_path}")
    print(f"Resumo JSON: {summary_path}")
    return 0


def main(arguments: Sequence[str] | None = None) -> int:
    parser = build_parser()
    config = build_config(parser.parse_args(arguments))
    try:
        return run(config)
    except ValueError as error:
        parser.error(str(error))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
