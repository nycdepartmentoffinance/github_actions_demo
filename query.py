import pandas as pd
import geopandas as gpd
import arcgis
from arcgis.gis import GIS
from arcgis.geometry import Polygon
import argparse
from shapely.validation import make_valid



layer_params = {
    "boro": {
        "collection": "e740addebac54632a5f216fd778af06d",
        "name": "NYC_Borough_Boundary",
        "fields": "OBJECTID, BoroCode, BoroName, Shape__Area, Shape__Length",
    },
    "nbhd": None,
    "block": {
        "collection": "2cf51c5f165c4c569691617a492d9b21",
        "name": "TAX_BLOCK_POLYGON",
        "fields": "OBJECTID, BORO, BLOCK, Shape__Area, Shape__Length",
    },
    "lot": {
        "collection": "2cf51c5f165c4c569691617a492d9b21",
        "name": "TAX_LOT_POLYGON",
        "fields": "OBJECTID, BORO, BLOCK, LOT, BBL, Shape__Area, Shape__Length",
    },
}


def extract_esri_shapes(geo_level, compute_centroids=False):
    """
    Extracts ESRI shapes (either neighborhoods or other geographic levels), optionally computes centroids,
    and exports the result as a compressed Parquet file.

    Parameters:
        geo_level (str): Geographic level to extract. Supports "nbhd" and other levels defined in `layer_params`.
        compute_centroids (bool): If True, compute centroids instead of using original polygons.

    Returns:
        str: Path to the output Parquet file or an error message if the collection is not public.
    """
    print(f"Starting extraction for geo_level: '{geo_level}' with centroids: {compute_centroids}")

    if geo_level == "nbhd":
        print("Reading neighborhood shapefile from local disk...")
        gdf = gpd.read_file("input/DOF_NBHD_Dissolved/DOF_NBHD_Dissolved.shp")
        gdf = gdf.rename(
            columns={"Shape_Leng": "Shape__Length", "Shape_Area": "Shape__Area"}
        )
        gdf["OBJECTID"] = range(1, len(gdf) + 1)
        print(f"Shapefile loaded with {len(gdf)} features.")

    else:
        print("Accessing ArcGIS Online content...")
        gis = GIS(timeout=10000)

        collection_id = layer_params.get(geo_level, {}).get("collection", None)
        collection = gis.content.get(collection_id)

        if collection.access != "public":
            print(f"Collection '{collection.title}' is not public. Aborting.")
            return f"Collection {collection.title} is not public"

        print(f"Fetching layer for geo_level: {geo_level}")
        layer_dict = {layer.properties.name: layer for layer in collection.layers}

        layer_name = layer_params.get(geo_level, {}).get("name", None)
        layer = layer_dict.get(layer_name, None)

        crs = layer.properties.extent.spatialReference["latestWkid"]
        print(f"Using CRS EPSG:{crs}")

        fields = layer_params.get(geo_level, {}).get("fields", None)
        print("Querying feature layer...")
        geo_data = layer.query(where="1=1", out_fields=fields, return_geometry=True)

        attr = [f.attributes for f in geo_data.features]
        geometries = [
            Polygon(f.geometry).as_shapely if f.geometry else None
            for f in geo_data.features
        ]

        gdf = gpd.GeoDataFrame(attr, geometry=geometries, crs=f"EPSG:{crs}")
        print(f"GeoDataFrame created with {len(gdf)} features.")

        str_cols = ["BBL", "BORO"]
        for col in str_cols:
            if col in gdf.columns:
                gdf[col] = pd.to_numeric(gdf[col], errors="coerce", downcast="integer")
                print(f"Converted column {col} to numeric.")

    if compute_centroids:
        print("Computing centroids...")
        if not gdf.crs.is_projected:
            print("Converting to projected CRS for centroid calculation...")
            gdf = gdf.to_crs(epsg=2263)

        gdf["centroid"] = gdf.geometry.centroid
        gdf["centroid"] = gdf["centroid"].to_crs(epsg=4326)

        gdf = gdf.drop(["Shape__Area", "Shape__Length", "geometry"], axis=1)
        gdf = gdf.set_geometry("centroid")
        shape_suffix = "centroids"
        print("Centroids computed and set as geometry.")

        geometry = "centroid"
    else:
        shape_suffix = "polygons"
        print("Using original polygons.")

        geometry = "geometry"

    print("Ensuring output is in EPSG:4326...")
    gdf = gdf.to_crs(epsg=4326)

    print(f"Columns of GeoDataFrame: {gdf.columns.tolist()}")

    print("Removing null geometries and validating invalid geometries...")
    gdf = gdf[gdf.geometry.notnull()]

    invalid = ~gdf.geometry.is_valid
    print(f"Validating {invalid.sum()} geometries...")

    gdf.loc[invalid, geometry] = gdf.loc[invalid, geometry].apply(make_valid)

    print(f"{len(gdf)} non-null, valid geometries retained.")

    if geo_level == "lot":
        print("Replacing condo base BBLs with billing BBLs using crosswalk table...")
        condo_table = collection.tables[1]
        crosswalk = condo_table.query(
            where="1=1", out_fields="*", return_geometry=False
        ).sdf[["CONDO_BASE_BBL", "CONDO_BILLING_BBL"]]

        # convert to numeric
        crosswalk["CONDO_BASE_BBL"] = pd.to_numeric(crosswalk["CONDO_BASE_BBL"], errors='coerce', downcast='integer')
        crosswalk["CONDO_BILLING_BBL"] = pd.to_numeric(crosswalk["CONDO_BILLING_BBL"], errors='coerce', downcast='integer')

        gdf = pd.merge(gdf, crosswalk, left_on="BBL", right_on="CONDO_BASE_BBL", how="left")
        gdf['BBL'] = gdf['CONDO_BILLING_BBL'].combine_first(gdf['BBL'])
        print("BBLs updated using crosswalk.")

    output_path = f"output/{geo_level}_{shape_suffix}.parquet"
    print(f"Writing output to {output_path}...")
    gdf.to_parquet(output_path, engine="pyarrow", compression='gzip')
    print("Export complete.")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Build Geoparquet files from ESRI API")
    parser.add_argument(
        "geo_level", help="The geometry of aggregation (boro, nbhd, block, lot)"
    )

    parser.add_argument(
        "--centroids", action="store_true", help="output centroids from polygons"
    )

    args = parser.parse_args()

    extract_esri_shapes(args.geo_level, args.centroids)


if __name__ == "__main__":
    main()
