# Description
The current repository is part of the manuscript 

Stathakis D., Liakos L., Chalkias C., and Pafi M.,"A photopollution index based on weighted cumulative visibility to nightlight", SPIE Remote Sensing (2018). 

The script calculates the *Photo-Pollution Index (PPI)* based on a DEM and an Nighttime Lights raster. The DEM extent should at least cover the AOI expanded by the max_distance of viewshed analysis (*AOI.xmin-vwdist AOI.ymin-vwdist AOI.xmax+vwdist AOI.ymax+vwdist*).

# Keywords
Night-lights, photopollution, lights-pollution, OLS, VIIRS,index, PPI, GRASS, GIS, python, pygrass

# Software Prerequisites
- GRASS GIS 7.x

# Data Prerequisites
- A Digital Elevation Model raster
- An Nighttime Lights raster

# Usage
1. Configure your grass region to calculate photopollution index. The region should aligned with DEM raster i.e.:

`g.region -p n=4393200 s=4374600 w=2217400 e=2233800 align=srtmV3_3arc`

2. Execute the script inside a GRASS session :

`./r.photopol.py <srtm_raster> <nighttime_raster> <PPI_output_raster> <viewshed_max_distance>`



