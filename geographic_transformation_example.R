# Imports and set-up ----------------------------------------

# avoid scientific notation and read in env variables
options(scipen = 999)
readRenviron("C:/Users/BoydClaire/.Renviron")

library(stats)
library(glue)
library(dplyr)
library(janitor)
library(DBI)
library(odbc)
library(arrow)
library(sf)


indata = read.csv("data/FY2027/outer_borough/model_results/current_comp_values_2025-09-30.csv")


out_data = indata %>%
    sf::st_as_sf(coords = c("xcoord_block", "ycoord_block")) %>%
    #select(pid, geometry) %>%
    st_set_crs(2263) %>%
    st_transform(4326) %>%
    mutate(
        lat = sf::st_coordinates(geometry)[,2],
        long = sf::st_coordinates(geometry)[,1]
    ) %>%
    st_drop_geometry() %>%
    select(
        pid, lat, long, yvar, prediction, selected_comparable_yvar, selected_comparable_yvar_adjusted
    )

write.csv(out_data, "data/FY2027/outer_borough/model_results/current_comp_values_2025-09-30_reprojected.csv",
          row.names = FALSE)
