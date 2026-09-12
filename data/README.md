# QuantumRoute Data Foundation — Verification Status

Last verified: 2026-09-11. Full source-by-source detail in `sources.yaml`.

## What is VERIFIED right now

- **METR-LA identity, license, structure**: confirmed live against the
  `liyaguang/DCRNN` GitHub repo (MIT license text, file existence/size),
  cross-checked against two independent academic papers (arXiv survey,
  PMC paper) for sensor count (207) and time range (2012-03-01 to
  2012-06-30, 5-min interval).
- **207 real sensor coordinates**: pulled from an MIT-licensed HuggingFace
  mirror and saved to `raw/metr_la/sensor_locations_VERIFIED_SAMPLE.csv`.
  Spot-checked against an independent citation (LibCity paper) for sensor
  `773869` — matched to 5 decimal places. Computed geographic extent
  (lat 34.043–34.222 N, lon 118.183–118.537 W) places every sensor in the
  San Fernando Valley area of LA, consistent with the US-101/I-405
  corridor description in the literature.
- **Only speed is measured** in the public METR-LA release — no volume,
  no occupancy. This is a real limitation, not an oversight.

## What is NOT yet verified (requires local execution — see below)

- The actual `metr-la.h5` readings file (missing-value %, real min/max/mean
  speed) — this sandbox cannot reach the Google Drive host it's stored on.
- The OSM road network for the sensor bounding box — this sandbox cannot
  reach the Overpass API.
- Sensor→edge map matching — depends on both of the above being downloaded first.

## Exact next steps (run locally, in order)

```bash
pip install osmnx==1.9.4 pandas tables gdown scipy pyproj shapely

# 1. Real OSM network, clipped exactly to the verified sensor bounding box
python scripts/download_osm_network.py \
    --bbox-from-sensors data/raw/metr_la/sensor_locations_VERIFIED_SAMPLE.csv \
    --buffer-km 2 \
    --out data/raw/osm/metr_la_network.graphml

# 2. Real traffic readings (see script docstring for the Drive file ID —
#    it's linked from the DCRNN README and changes occasionally)
gdown --id <FILE_ID> -O data/raw/metr_la/metr-la.h5
python scripts/download_traffic_data.py --check data/raw/metr_la/metr-la.h5

# 3. Once both exist, map matching becomes runnable
python -c "
import osmnx as ox, csv
from backend.app.data.map_matching import match_sensors_to_graph, summarize_matches
G = ox.load_graphml('data/raw/osm/metr_la_network.graphml')
G = ox.project_graph(G)
with open('data/raw/metr_la/sensor_locations_VERIFIED_SAMPLE.csv') as f:
    sensors = list(csv.DictReader(f))
for s in sensors:
    s['latitude'] = float(s['latitude']); s['longitude'] = float(s['longitude'])
results = match_sensors_to_graph(G, sensors)
print(summarize_matches(results))
"
```

Only after step 3 produces a real match-rate report do we proceed to
preprocessing, ML training, QUBO construction, and the optimizer — per
the project's stated priority order (data validity first).

## Attribution

Road network data: © OpenStreetMap contributors, ODbL v1.0.
Traffic data: Li, Yaguang, et al. "Diffusion Convolutional Recurrent
Neural Network: Data-Driven Traffic Forecasting." ICLR 2018. (MIT license)
