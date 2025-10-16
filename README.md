# GitHub Actions Demo -- Geospatial Data Transformation

This project automates the process to transform the up-to-date geometries from the [Digital Tax Map on ArcGIS Online](https://nyc.maps.arcgis.com/home/item.html?id=2cf51c5f165c4c569691617a492d9b21) to geo-dataframes that are easy to use in R or python.

This action is performed by the `query.py` script, which extracts geographic boundary data from the NYC Open Data ArcGIS API (or a local shapefile for neighborhoods) and exports it as compressed GeoParquet files. It supports different geographic levels, such as boroughs, neighborhoods, blocks, and lots, and includes an option to output centroids instead of full polygons.

There are two ways that this script can be run:

1. **Using a github action**: If you want to update all the files at once, you can run a pre-configured github action that will update all 8 files at once. To do this, click on the Actions tab above, click on `run-geo-query` below the "All workflows" section on the left. Click on `run workflow` and then `run workflow` again, using the main branch for the action. The action will take ~20 minutes to run, but then all the parquet files in the `output/` folder will be updated with the latest geographies.
    
    *Note: this action is already set to run weekly, so if a weekly update is all you need, you can use the existing parquet files*.
2. **On the command line**: If you want to have a bit more control over which specific files you want updated, you can run the script from the command line. First, you need to git clone this repository:
    ```bash
    git clone https://github.com/nycdepartmentoffinance/geospatial_data.git
    ```
    And then you can run the script, using it's own virtual environment, by using the following command:
    ```cmd
    uv run query.py [arg 1] [arg 2] 
    ```
    `arg 1` is the geographic level, so you can specify either boro, block, nbhd, or lot. `arg 2` is either `--centroids` if you want centroids of each geography or nothing for polygons (this is the default). 
    
    For example if I wanted to update the block polygon file I would use the following:
    ```bash
    uv run query.py block
    ```
    If I wanted to update the block centroid file, I would run the following:
    ```bash
    uv run query.py block --centroid
    ```


**Note: The script is currectly set up to run weekly using the github action.**

## Using the `.parquet` files

Great! Now that the parquet files are ready to use, we can read them in using either python or R to make maps or other visualizations.

### Python

To import any of the shapefiles as a geodataframe using the `geopandas` library in python, you can do the following:

```python
import geopandas as gpd

blocks = gpd.read_parquet("output/block_polygons.parquet")
```

Now that you have it read in locally as a geodataframe, you can convert it into a static map or an interactive map using one of pythons mapping libraries, including `matplotlib` or `plotly`. For an example of how to create really basic maps with the block polygons, explore [python_maps.ipynb](python_maps.ipynb).

### R

To import a parquet file as an equivalent geodataframe in R, you need to do the following in an R script:

```r
library(arrow)
library(sf)
library(leaflet)
library(dplyr)

parquet_file = "output/block_polygons.parquet"
df <- arrow::read_parquet(parquet_file, as_tibble = TRUE) %>%
   dplyr::mutate(
       geom = sf::st_as_sfc(geometry, EWKB = TRUE)
   ) %>%
   dplyr::select(-geometry, -OBJECTID, -`__index_level_0__`) %>%
   rename(
       geometry = geom
   )
gdf = sf::st_as_sf(df, geometry=df$geometry)
```
*Note: As you can see, the R approach requires a few more lines of code to read in the parquet file properly, but once you have it saved correctly, it is in a very versatile format.*

If you want to play around with mapping, look at the [R_maps.Rmd](R_maps.Rmd) file for inspiration - just like the python example, there are static and interactive maps available using open source R libraries, like `ggplot2` and `leaflet`.
