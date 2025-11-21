# Phase 3: Hyperlocal Data Fetching with OSMnx

## Overview

Phase 3 of the Delhi-NCR AQI Assessment project focuses on extracting hyperlocal contextual features around air quality monitoring stations using OpenStreetMap (OSM) data via the OSMnx library. This process captures fine-grained urban characteristics within a small buffer radius (typically 100 meters) around each monitoring station, providing spatial context that can influence air quality measurements.

## Purpose

The hyperlocal feature extraction process aims to:

- **Capture spatial context**: Understand the immediate environment surrounding each air quality monitoring station
- **Extract road/traffic features**: Measure proximity to major roads and total road infrastructure
- **Analyze land use patterns**: Quantify green space, industrial, and residential land use percentages
- **Assess building morphology**: Calculate building density, sizes, and counts within the buffer zone
- **Support AQI modeling**: Provide features that can help explain spatial variations in air quality measurements

## Dependencies

The following Python packages are required:

```python
osmnx          # OpenStreetMap data extraction
geopandas      # Geospatial data manipulation
shapely        # Geometric operations
rtree          # Spatial indexing
pyproj         # Coordinate reference system transformations
pandas         # Data manipulation
numpy          # Numerical operations
tqdm           # Progress bars
```

Install with:
```bash
pip install osmnx geopandas shapely rtree pyproj pandas tqdm
```

## Setup and Configuration

### OSMnx Configuration

The notebook configures OSMnx with the following settings:

```python
ox.settings.use_cache = True
ox.settings.cache_folder = "./osm_cache"
ox.settings.log_console = False
ox.settings.timeout = 180
ox.settings.overpass_endpoint = "https://overpass.private.coffee/api/interpreter"
```

**Key Settings:**
- **Caching**: Enabled to avoid redundant API calls and speed up repeated queries
- **Cache folder**: Stores downloaded OSM data locally in `./osm_cache`
- **Timeout**: 180 seconds for Overpass API queries
- **Overpass endpoint**: Uses a private Overpass API instance for better reliability

## Data Input

### Monitoring Stations

The process operates on a list of 7 air quality monitoring stations across Delhi-NCR:

1. **Anand Vihar, Delhi (DPCC / CPCB)** - 28.6559°N, 77.2949°E
2. **Punjabi Bagh, Delhi (DPCC)** - 28.674°N, 77.131°E
3. **Mandir Marg, Delhi (DPCC)** - 28.636429°N, 77.201067°E
4. **R K Puram, Delhi (DPCC)** - 28.563262°N, 77.186937°E
5. **Sector-51 Gurugram (HSPCB)** - 28.43518°N, 77.072°E
6. **Vikas Sadan Gurugram (HSPCB)** - 28.450129°N, 77.026306°E
7. **Sector-125 Noida (UPPCB)** - 28.5897°N, 77.31°E

Stations are converted to a GeoDataFrame with WGS84 (EPSG:4326) coordinate reference system.

## Core Functions

### 1. Coordinate Reference System Utilities

#### `get_utm_crs_for_point(lat, lon)`
Returns an appropriate UTM (Universal Transverse Mercator) CRS for accurate metric measurements at a given location.

- **Purpose**: UTM projections provide accurate distance and area measurements in meters
- **Method**: Uses OSMnx's built-in UTM selection based on latitude/longitude
- **Fallback**: EPSG:3857 (Web Mercator) if UTM selection fails

#### `make_buffer(point_geom, meters=500)`
Creates a circular buffer polygon around a point geometry.

**Process:**
1. Projects point from WGS84 to local UTM CRS
2. Creates buffer in UTM (accurate metric radius)
3. Reprojects buffer back to WGS84
4. Validates geometry and checks size constraints
5. Raises error if buffer exceeds ~5km threshold (prevents Overpass API issues)

**Parameters:**
- `point_geom`: Shapely Point geometry in WGS84
- `meters`: Buffer radius in meters (default: 500m, typically 100m for hyperlocal analysis)

#### `area_m2(geom)`
Calculates the area of a geometry in square meters by projecting to UTM.

## Feature Extraction Functions

### 2. Road and Traffic Features

#### `compute_road_features(point_row, buffer_poly)`

Extracts road infrastructure characteristics within the buffer zone.

**Process:**
1. **Query OSM**: Fetches all highway features within the buffer bounding box
2. **Filter geometries**: Keeps only LineString and MultiLineString geometries
3. **Intersect with buffer**: Clips road segments to buffer polygon boundaries
4. **Calculate lengths**: Projects segments to UTM and measures lengths in meters
5. **Classify major roads**: Identifies major highways (motorway, trunk, primary, secondary, tertiary)
6. **Compute distance**: Calculates minimum distance from station to nearest major road

**Output Features:**
- `distance_to_major_road` (meters): Minimum distance to nearest major road
- `total_road_length_m` (meters): Total length of all roads within buffer
- `major_road_length_m` (meters): Total length of major roads only

**Major Road Types:**
- `motorway`: High-speed, controlled-access highways
- `trunk`: Major highways
- `primary`: Primary roads
- `secondary`: Secondary roads
- `tertiary`: Tertiary roads

### 3. Land Use Features

#### `compute_landuse_features(buffer_poly)`

Analyzes land use and land cover patterns using OSM tags as a proxy for LULC (Land Use/Land Cover).

**Process:**
1. **Query OSM**: Fetches features tagged with `landuse`, `leisure`, or `natural`
2. **Filter polygons**: Keeps only Polygon and MultiPolygon geometries
3. **Intersect with buffer**: Computes intersection areas
4. **Project to UTM**: Calculates areas in square meters
5. **Classify by keywords**: Categorizes features into:
   - **Green space**: forest, grass, park, recreation, garden, meadow, wood, green
   - **Industrial**: industrial, quarry, landfill
   - **Residential**: residential, housing, residential;apartments
6. **Calculate percentages**: Computes fraction of total area for each category

**Output Features:**
- `pct_green` (0-1): Fraction of buffer area classified as green space
- `pct_industrial` (0-1): Fraction classified as industrial
- `pct_residential` (0-1): Fraction classified as residential

**Note**: OSM land use tags are a proxy for authoritative LULC data. For production use, consider using satellite-derived LULC raster data with zonal statistics.

### 4. Building Morphology Features

#### `compute_building_features(buffer_poly)`

Analyzes building footprints and urban density.

**Process:**
1. **Query OSM**: Fetches all building features within bounding box
2. **Filter polygons**: Keeps only Polygon and MultiPolygon geometries
3. **Intersect with buffer**: Clips building footprints to buffer boundaries
4. **Calculate areas**: Projects to UTM and computes building areas in square meters
5. **Compute statistics**: Calculates density, average, median, and count

**Output Features:**
- `building_density` (0-1): Fraction of buffer area covered by building footprints
- `avg_building_area_m2` (square meters): Average building footprint area
- `median_building_area_m2` (square meters): Median building footprint area
- `building_count` (integer): Number of buildings within buffer

## Processing Pipeline

### Main Execution Loop

The pipeline processes each monitoring station sequentially:

```python
buffer_radius_m = 1000  # meters

for each station:
    1. Create buffer polygon around station point
    2. Extract road features
    3. Extract land use features
    4. Extract building features
    5. Combine all features into result dictionary
    6. Pause 1 second (rate limiting for Overpass API)
```

**Error Handling:**
- Buffer creation failures: Returns NaN/zero values for all features
- OSM query failures: Catches exceptions and returns default values
- Empty results: Handles cases where no features are found

### Rate Limiting

A 1-second pause between stations prevents overwhelming the Overpass API:
```python
time.sleep(1.0)
```

## Output

### Results DataFrame

The pipeline generates a pandas DataFrame with the following columns:

**Station Information:**
- `station`: Station name
- `lat`: Latitude
- `lon`: Longitude
- `notes`: Source/notes about station location

**Road Features:**
- `distance_to_major_road`: Distance to nearest major road (meters)
- `total_road_length_m`: Total road length (meters)
- `major_road_length_m`: Major road length (meters)
- `major_road_fraction`: Derived feature (major_road_length / total_road_length)

**Land Use Features:**
- `pct_green`: Green space percentage (0-1)
- `pct_industrial`: Industrial land use percentage (0-1)
- `pct_residential`: Residential land use percentage (0-1)

**Building Features:**
- `building_density`: Building footprint density (0-1)
- `avg_building_area_m2`: Average building area (square meters)
- `median_building_area_m2`: Median building area (square meters)
- `building_count`: Number of buildings

### Output File

Results are saved to CSV:
```
delhi_hyperlocal_context_features.csv
```

## Technical Considerations

### Coordinate Systems

- **Input/Output**: WGS84 (EPSG:4326) - standard GPS coordinates
- **Computations**: Local UTM zones for accurate metric measurements
- **Transformations**: Automatic CRS selection based on station location

### Geometry Validation

- Buffers are validated and cleaned using `buffer(0)` operation
- Size constraints prevent queries that exceed Overpass API limits
- Empty geometries are filtered out at each step

### Data Quality

**Strengths:**
- OSM data is community-maintained and frequently updated
- Provides detailed urban infrastructure information
- Free and openly available

**Limitations:**
- Coverage may vary by region (urban areas typically better mapped)
- Tagging consistency can vary
- Land use tags are less authoritative than satellite-derived LULC
- Some areas may have incomplete building or road data

### Performance

- **Caching**: OSMnx caches queries to avoid redundant API calls
- **Processing time**: ~2-5 minutes per station (depends on API response time)
- **Total time**: ~15-25 minutes for 7 stations with 100m buffer

### Error Handling

The pipeline includes comprehensive error handling:
- OSM query failures return NaN/zero values
- Geometry validation prevents invalid operations
- Size checks prevent API overload
- Individual station failures don't stop the entire pipeline

## Usage Example

```python
# Set buffer radius
buffer_radius_m = 100

# Process all stations
results = []
for idx, row in tqdm(gdf_stations.iterrows(), total=len(gdf_stations)):
    buffer_poly = make_buffer(row.geometry, meters=buffer_radius_m)
    
    road_feats = compute_road_features(row, buffer_poly)
    land_feats = compute_landuse_features(buffer_poly)
    bld_feats = compute_building_features(buffer_poly)
    
    result = {**row.to_dict(), **road_feats, **land_feats, **bld_feats}
    results.append(result)
    time.sleep(1.0)

# Save results
df_results = pd.DataFrame(results)
df_results.to_csv('delhi_hyperlocal_context_features.csv', index=False)
```

## Next Steps

The extracted hyperlocal features can be used for:

1. **Feature Engineering**: Combine with satellite-derived AQI data
2. **Spatial Analysis**: Understand relationships between urban form and air quality
3. **Modeling**: Use as predictor variables in AQI prediction models
4. **Visualization**: Create maps showing spatial context around stations

## References

- [OSMnx Documentation](https://osmnx.readthedocs.io/)
- [OpenStreetMap Wiki](https://wiki.openstreetmap.org/)
- [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API)
- [GeoPandas Documentation](https://geopandas.org/)

