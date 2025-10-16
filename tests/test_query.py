import geopandas as gpd
from pyproj import CRS
from shapely import MultiPolygon, Polygon, Point
import os

expected_files = ['block_centroids.parquet',
 'block_polygons.parquet',
 'boro_centroids.parquet',
 'boro_polygons.parquet',
 'lot_centroids.parquet',
 'lot_polygons.parquet']

output_list = os.listdir('output')

def test_filelist():
    missing_files = set(expected_files) - set(output_list)

    assert not missing_files, f'Missing files: {missing_files}'

def test_gdf():
    for file in output_list:
        gdf = gpd.read_parquet(f'output/{file}')
        assert isinstance(gdf, gpd.GeoDataFrame)

def test_crs():
    for file in output_list:
        gdf = gpd.read_parquet(f'output/{file}')
        assert gdf.crs == CRS('EPSG:4326')

def test_shape():
    print(output_list)
    for file in output_list:
        gdf = gpd.read_parquet(f'output/{file}')
        print(file)
        if file.endswith('_polygons.parquet'):
            assert all(isinstance(geom, (Polygon, MultiPolygon)) for geom in gdf.geometry)
        elif file.endswith('_centroids.parquet'):
            assert all(isinstance(geom, Point) for geom in gdf.geometry)

