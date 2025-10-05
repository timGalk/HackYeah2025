# Incident Reporting API

Async FastAPI service that stores incident reports in Elasticsearch.

## Getting Started

Run the API, Elasticsearch, and Kibana stack:

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`, Elasticsearch at `http://localhost:9200`, and Kibana at `http://localhost:5601`.

## API Endpoints

### POST /api/v1/incidents
Submit a new incident report.

- **Request Body**
  ```json
  {
    "latitude": 52.2297,
    "longitude": 21.0122,
    "description": "Road blocked by fallen tree",
    "category": "infrastructure",
    "username": "janedoe",
    "approved": false
  }
  ```
- **Success Response** `201 Created`
  ```json
  {
    "incident_id": "abc123"
  }
  ```

### GET /api/v1/incidents
Return all incidents ordered by their creation timestamp.

### GET /api/v1/incidents/latest?limit=<N>
Return the `N` most recent incidents (`limit` defaults to 10 and caps at 1000).

### GET /api/v1/incidents/range?start=<ISO8601>&end=<ISO8601>
Return incidents whose `created_at` falls within the inclusive interval.

### GET /api/v1/transport/modes
List transport graph modes that were constructed at application startup.

- **Success Response** `200 OK`
  ```json
  {
    "modes": ["bus", "tram", "walking", "bike"]
  }
  ```

### PATCH /api/v1/transport/graphs/{mode}/edges/{source}/{target}
Adjust the weight or traversal speed of an edge in a transport graph. When a speed is
provided the service recalculates the weight using stored distance metadata.

- **Request Body**
  ```json
  {
    "key": "walk-stop_a-stop_b",
    "speed_kmh": 6.0
  }
  ```
- **Success Response** `200 OK`
  ```json
  {
    "edge": {
      "mode": "walking",
      "source": "stop_a",
      "target": "stop_b",
      "key": "walk-stop_a-stop_b",
      "weight": 150.0,
      "speed_kmh": 6.0,
      "distance_km": 0.25
    }
  }
  ```

### PATCH /api/v1/transport/graphs/nearest
Update the nearest transit edge (excluding walking and biking) to the provided
coordinates with a new weight.

- **Request Body**
  ```json
  {
    "latitude": 50.062,
    "longitude": 19.938,
    "weight": 220.0
  }
  ```
- **Success Response** `200 OK`
  ```json
  {
    "edge": {
      "mode": "tram",
      "source": "stop_a",
      "target": "stop_b",
      "key": "trip-123",
      "weight": 220.0,
      "distance_to_point_km": 0.03
    }
  }
  ```

### POST /api/v1/transport/graphs/nearest/lookup
Return the closest transit edge (excluding walking and biking) to a point without
modifying the graph.

- **Request Body**
  ```json
  {
    "latitude": 50.062,
    "longitude": 19.938
  }
  ```
- **Success Response** `200 OK`
  ```json
  {
    "edge": {
      "mode": "tram",
      "source": "stop_a",
      "target": "stop_b",
      "key": "trip-123",
      "weight": 220.0,
      "distance_to_point_km": 0.03
    }
  }
  ```

### GET /api/v1/transport/graphs?mode=<mode>
Return a snapshot of the serialized graphs. When `mode` is omitted the response includes
all available modes.

### WebSocket /api/v1/transport/graphs/stream
Streams a snapshot followed by incremental edge updates, enabling live visualisations.

### GET /api/v1/transport/visualizer
Serves an interactive HTML dashboard for exploring the transport graph and issuing
edge updates in real time.

## Configuration

Environment variables can adjust runtime behaviour:

- `ELASTICSEARCH_URL` – Elasticsearch connection string (default `http://elasticsearch:9200`).
- `ELASTICSEARCH_INDEX` – Target index for incident documents (default `incidents`).
- `APP_VERSION` – Overrides the reported application version.
- `GTFS_FEED_PATH` – Location of the GTFS zip feed used to build transport graphs (default `otp_data/GTFS_KRK_A.zip`).
- `WALKING_SPEED_KMH` – Average walking speed used for graph weights (default `5.0`).
- `BIKE_SPEED_KMH` – Average bike speed when parkings are nearby (default `20.0`).
- `BIKE_ACCESS_RADIUS_M` – Radius in metres to flag a stop as bike-accessible (default `150`).
- `BIKE_PARKINGS_PATH` – Optional JSON/GeoJSON file describing bike parking locations.

## Kibana Access

After the stack starts, browse to `http://localhost:5601` for Kibana. Use the preconfigured Elasticsearch host to explore the `incidents` index.
