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

## Configuration

Environment variables can adjust runtime behaviour:

- `ELASTICSEARCH_URL` – Elasticsearch connection string (default `http://elasticsearch:9200`).
- `ELASTICSEARCH_INDEX` – Target index for incident documents (default `incidents`).
- `APP_VERSION` – Overrides the reported application version.

## Kibana Access

After the stack starts, browse to `http://localhost:5601` for Kibana. Use the preconfigured Elasticsearch host to explore the `incidents` index.
