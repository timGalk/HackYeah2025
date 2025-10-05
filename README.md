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
    "description": "Heavy traffic congestion on main road",
    "category": "Traffic",
    "username": "janedoe",
    "approved": false,
    "reporter_social_score": 12.5
  }
  ```
- **Success Response** `201 Created`
  ```json
  {
    "incident_id": "abc123"
  }
  ```
- **Valid Categories and Impact**
  - `Traffic` – Applies a 1.5× edge weight multiplier; requires combined `reporter_social_score` ≥ 50.0 to activate (unless `approved: true`).
  - `Crush` – Applies an extremely large edge weight multiplier (effectively blocks the route); activates immediately regardless of social score.
  - Other category values are accepted but do not influence transport graphs.
- **Notes**
  - Unapproved incidents influence transport edges only when the combined
    `reporter_social_score` of reporters within the same category exceeds the configured
    acceptance threshold.
  - Approved incidents (`approved: true`) bypass the social score threshold and apply their multiplier immediately.

### GET /api/v1/incidents
Return all incidents ordered by their creation timestamp.

- **Query Parameters**
  - `coordinates` *(optional, repeatable)* – One or more coordinate pairs in 'latitude,longitude' format. When provided, only incidents on routes that pass within 1km of any coordinate are returned.
  - `max_distance_km` *(optional)* – Maximum distance in kilometers from coordinates to consider routes (default: 1.0, range: 0.1-10.0).
- **Success Response** `200 OK`
  ```json
  {
    "incidents": [
      {
        "id": "abc123",
        "latitude": 52.2297,
        "longitude": 21.0122,
        "description": "Road blocked by fallen tree",
        "category": "infrastructure",
        "username": "janedoe",
        "approved": false,
        "created_at": "2024-01-05T12:14:32.000000",
        "edge_mode": "tram",
        "edge_source": "stop_a",
        "edge_target": "stop_b",
        "edge_key": "trip-123",
        "trip_id": "trip-123",
        "route_id": "T4",
        "route_short_name": "4",
        "route_long_name": "Kurdwanów - Bronowice Małe",
        "impacted_routes": ["T4"]
      }
    ]
  }
  ```

### GET /api/v1/incidents/latest?limit=<N>
Return the `N` most recent incidents (`limit` defaults to 10 and caps at 1000).

- **Query Parameters**
  - `coordinates` *(optional, repeatable)* – One or more coordinate pairs in 'latitude,longitude' format. When provided, only incidents on routes that pass within 1km of any coordinate are returned.
  - `max_distance_km` *(optional)* – Maximum distance in kilometers from coordinates to consider routes (default: 1.0, range: 0.1-10.0).

### GET /api/v1/incidents/range?start=<ISO8601>&end=<ISO8601>
Return incidents whose `created_at` falls within the inclusive interval.

- **Query Parameters**
  - `coordinates` *(optional, repeatable)* – One or more coordinate pairs in 'latitude,longitude' format. When provided, only incidents on routes that pass within 1km of any coordinate are returned.
  - `max_distance_km` *(optional)* – Maximum distance in kilometers from coordinates to consider routes (default: 1.0, range: 0.1-10.0).

### POST /api/v1/facebook-posts/upload
Upload Facebook posts into Elasticsearch using mock data or a future live scraper.

- **Request Body**
  ```json
  {
    "source": "mock"
  }
  ```
- **Success Response** `200 OK`
  ```json
  {
    "uploaded": 10,
    "source": "mock",
    "warning": null
  }
  ```
- **Notes**
  - When `source` is set to `scrape`, the endpoint returns a warning message because
    live scraping is not implemented yet. The request still succeeds without ingesting
    new posts.
  - Mock uploads read data from `src/scrapper/parsed_posts.json` and write documents to
    the `facebook_posts` Elasticsearch index.

### GET /api/v1/users/{user_id}/routes
Return the planned and frequent routes configured for a user.

- **Query Parameters**
  - `kinds` *(optional, repeatable)* – Filter to one or both preference types (`planned`, `frequent`).
- **Success Response** `200 OK`
  ```json
  {
    "preferences": [
      {
        "id": "user-123::T4::frequent",
        "user_id": "user-123",
        "route_id": "T4",
        "route_short_name": "4",
        "route_long_name": "Kurdwanów - Bronowice Małe",
        "kind": "frequent",
        "notes": null,
        "created_at": "2024-01-05T12:14:32.000000",
        "updated_at": "2024-01-05T12:14:32.000000"
      }
    ]
  }
  ```

### PUT /api/v1/users/{user_id}/routes
Create or update a planned/frequent route for the user (idempotent).

- **Request Body**
  ```json
  {
    "user_id": "user-123",
    "route_id": "T4",
    "route_short_name": "4",
    "route_long_name": "Kurdwanów - Bronowice Małe",
    "kind": "frequent",
    "notes": "Morning commute"
  }
  ```
- **Success Response** `201 Created`
  ```json
  {
    "id": "user-123::T4::frequent",
    "user_id": "user-123",
    "route_id": "T4",
    "route_short_name": "4",
    "route_long_name": "Kurdwanów - Bronowice Małe",
    "kind": "frequent",
    "notes": "Morning commute",
    "created_at": "2024-01-05T12:14:32.000000",
    "updated_at": "2024-01-05T12:15:10.000000"
  }
  ```

### DELETE /api/v1/users/{user_id}/routes/{kind}/{route_id}
Remove a planned or frequent route preference.

- **Success Response** `200 OK`
  ```json
  {
    "deleted": true
  }
  ```

### GET /api/v1/transport/modes
List transport graph modes that were constructed at application startup.

- **Success Response** `200 OK`
  ```json
  {
    "modes": ["bike", "bus", "walking"]
  }
  ```
- **Notes**
  - Available modes depend on the GTFS feed and configuration
  - Common modes include: `bus`, `bike`, `walking`
  - Mode availability may vary based on data availability

### GET /api/v1/transport/routes?mode=<mode>&source=<source>&target=<target>
Plan a route within a transport mode and flag segments slowed down by incidents. When
the default path crosses impacted edges the response proposes an alternative route that
avoids them, if possible.

- **Query Parameters**
  - `mode` – Required transport mode label (e.g. `bus`).
  - `source` – Required identifier of the starting node.
  - `target` – Required identifier of the destination node.
- **Success Response** `200 OK`
  ```json
  {
    "incident_detected": true,
    "message": "Incidents detected on the default path; alternative route suggested.",
    "default_path": {
      "nodes": ["stop_a", "stop_b", "stop_c"],
      "segments": [
        {
          "source": "stop_a",
          "target": "stop_b",
          "key": "trip-101",
          "mode": "bus",
          "default_weight": 120.0,
          "current_weight": 320.0,
          "impacted": true,
          "distance_km": 1.5,
          "speed_kmh": 17.0,
          "connector": null,
          "metadata": {
            "route_id": "R1"
          }
        },
        {
          "source": "stop_b",
          "target": "stop_c",
          "key": "trip-102",
          "mode": "bus",
          "default_weight": 110.0,
          "current_weight": 110.0,
          "impacted": false,
          "distance_km": 1.3,
          "speed_kmh": 20.0,
          "connector": null,
          "metadata": null
        }
      ],
      "total_default_weight": 230.0,
      "total_current_weight": 430.0
    },
    "suggested_path": {
      "nodes": ["stop_a", "stop_d", "stop_c"],
      "segments": [
        {
          "source": "stop_a",
          "target": "stop_d",
          "key": "trip-201",
          "mode": "bus",
          "default_weight": 140.0,
          "current_weight": 140.0,
          "impacted": false,
          "distance_km": 1.6,
          "speed_kmh": 21.0,
          "connector": null,
          "metadata": {
            "route_id": "R2"
          }
        },
        {
          "source": "stop_d",
          "target": "stop_c",
          "key": "trip-202",
          "mode": "bus",
          "default_weight": 130.0,
          "current_weight": 130.0,
          "impacted": false,
          "distance_km": 1.4,
          "speed_kmh": 22.0,
          "connector": null,
          "metadata": null
        }
      ],
      "total_default_weight": 270.0,
      "total_current_weight": 270.0
    }
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

### GET /admin/incidents
Render a lightweight HTML admin panel listing all incidents with their current approval
state. Each entry displays key details alongside an action button to approve pending
incidents or revoke approval. Approved incidents immediately affect transport edges
regardless of reporter score, and revoking the approval restores social-score gating.

### POST /admin/incidents/{incident_id}/approve
Approve the referenced incident and redirect back to the admin panel. Incidents already
approved are treated as no-ops. Granting approval increases the reporter's social score
by 10 points the first time an incident is approved.

### POST /admin/incidents/{incident_id}/revoke
Revoke approval for the referenced incident and redirect back to the admin panel. If the
incident was already unapproved, the request is a no-op.

### POST /admin/incidents/purge
Remove incidents either across the entire index or within a supplied time range. When
`start` and `end` fields are supplied (ISO8601), only incidents within that interval are
deleted; otherwise the entire index is cleared.

### DELETE /admin/incidents/api
Programmatic equivalent of the purge form. Accepts an optional JSON body with `start`
and `end` properties (`ISO8601` strings). When omitted, all incidents are deleted. The
response contains the number of documents removed and the applied scope.

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
- `INCIDENT_POLL_INTERVAL_SECONDS` – Interval for polling incidents to update transport graphs (default `60`).

## Kibana Access

After the stack starts, browse to `http://localhost:5601` for Kibana. Use the preconfigured Elasticsearch host to explore the `incidents` index.
