"""Transport graph management API routes."""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import HTMLResponse

from app.api.dependencies import get_transport_graph_service
from app.schemas.transport import (
    AvailableModesResponse,
    ClosestEdgeUpdatePayload,
    ClosestEdgeUpdateResponse,
    ClosestEdgeLookupPayload,
    ClosestEdgeLookupResponse,
    EdgeDetail,
    EdgeErrorResponse,
    EdgeUpdatePayload,
    EdgeUpdateResponse,
    GraphSnapshotResponse,
    RoutePlanResponse,
)
from app.services.transport import TransportGraphService

router = APIRouter(prefix="/transport", tags=["transport"])

VISUALIZER_HTML = """
<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <title>Transport Graph Visualizer</title>
    <script src=\"https://unpkg.com/vis-network/standalone/umd/vis-network.min.js\"></script>
    <style>
      body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
      header { background: #1f2933; color: #fff; padding: 12px 24px; }
      main { display: flex; flex-direction: row; height: calc(100vh - 60px); }
      #network { flex: 1; background: #f4f5f7; }
      aside { width: 360px; padding: 16px; overflow-y: auto; border-left: 1px solid #d9dce1; }
      label { font-size: 0.85rem; display: block; margin: 12px 0 4px; color: #1f2933; }
      select, input, button {
        width: 100%;
        padding: 8px;
        margin-bottom: 8px;
        box-sizing: border-box;
      }
      button { background: #2563eb; color: #fff; border: none; cursor: pointer; font-weight: 600; }
      button:hover { background: #1d4ed8; }
      #status { margin-top: 12px; font-size: 0.85rem; min-height: 32px; color: #374151; }
      .section { margin-bottom: 24px; }
      .hint { font-size: 0.75rem; color: #6b7280; }
    </style>
  </head>
  <body>
    <header>
      <h1>Transport Graph Visualizer</h1>
    </header>
    <main>
      <div id=\"network\"></div>
      <aside>
        <div class=\"section\">
          <label for=\"modeSelect\">Transport mode</label>
          <select id=\"modeSelect\"></select>
          <p class=\"hint\">Graph updates stream automatically while this tab is open.</p>
        </div>
        <div class=\"section\">
          <h2>Update specific edge</h2>
          <form id=\"edgeForm\">
            <label for=\"edgeMode\">Mode</label>
            <input id=\"edgeMode\" name=\"edgeMode\" required />
            <label for=\"edgeSource\">Source stop id</label>
            <input id=\"edgeSource\" name=\"edgeSource\" required />
            <label for=\"edgeTarget\">Target stop id</label>
            <input id=\"edgeTarget\" name=\"edgeTarget\" required />
            <label for=\"edgeKey\">Edge key (optional)</label>
            <input id=\"edgeKey\" name=\"edgeKey\" />
            <label for=\"edgeWeight\">Weight seconds (optional)</label>
            <input id=\"edgeWeight\" name=\"edgeWeight\" type=\"number\" step=\"0.01\" />
            <label for=\"edgeSpeed\">Speed km/h (optional)</label>
            <input id=\"edgeSpeed\" name=\"edgeSpeed\" type=\"number\" step=\"0.1\" />
            <button type=\"submit\">Patch edge</button>
          </form>
        </div>
        <div class=\"section\">
          <h2>Update nearest transit edge</h2>
          <form id=\"nearestForm\">
            <label for=\"latitude\">Latitude</label>
            <input id=\"latitude\" name=\"latitude\" type=\"number\" step=\"0.0001\" required />
            <label for=\"longitude\">Longitude</label>
            <input id=\"longitude\" name=\"longitude\" type=\"number\" step=\"0.0001\" required />
            <label for=\"nearestWeight\">Weight seconds</label>
            <input
              id=\"nearestWeight\"
              name=\"nearestWeight\"
              type=\"number\"
              step=\"0.01\"
              required
            />
            <button type=\"submit\">Apply nearest update</button>
          </form>
        </div>
        <div id=\"status\"></div>
      </aside>
    </main>
    <script>
      const modeSelect = document.getElementById('modeSelect');
      const edgeModeInput = document.getElementById('edgeMode');
      const networkContainer = document.getElementById('network');
      const statusBox = document.getElementById('status');
      const nodesDataset = new vis.DataSet();
      const edgesDataset = new vis.DataSet();
      let network = null;
      let selectedMode = null;
      let socket = null;

      const networkOptions = {
        physics: false,
        interaction: { hover: true },
        edges: { smooth: false },
      };

      function edgeId(edge) {
        const modeLabel = edge.mode ?? selectedMode ?? 'unknown';
        return `${modeLabel}|${edge.source}|${edge.target}|${edge.key}`;
      }

      function renderGraph(graph) {
        const nodes = graph.nodes.map((node) => {
          const hasPosition = node.latitude !== null && node.latitude !== undefined &&
            node.longitude !== null && node.longitude !== undefined;
          return {
            id: node.id,
            label: node.id,
            x: hasPosition ? node.longitude * 10000 : undefined,
            y: hasPosition ? -node.latitude * 10000 : undefined,
            fixed: hasPosition,
            color: node.bike_accessible ? '#2ecc71' : '#2563eb',
          };
        });
        const edges = graph.edges.map((edge) => ({
          id: edgeId(edge),
          from: edge.source,
          to: edge.target,
          arrows: 'to',
          label: typeof edge.weight === 'number' ? `${edge.weight.toFixed(1)}s` : '',
          color: edge.connector ? '#e74c3c' : '#4b5563',
        }));
        nodesDataset.clear();
        nodesDataset.add(nodes);
        edgesDataset.clear();
        edgesDataset.add(edges);
        if (!network) {
          network = new vis.Network(networkContainer, {
            nodes: nodesDataset,
            edges: edgesDataset,
          }, networkOptions);
        } else {
          network.setData({ nodes: nodesDataset, edges: edgesDataset });
        }
      }

      function applyEdgeUpdate(edge) {
        if (!selectedMode || (edge.mode && edge.mode !== selectedMode)) {
          return;
        }
        const id = edgeId(edge);
        const payload = {
          id,
          from: edge.source,
          to: edge.target,
          arrows: 'to',
          label: typeof edge.weight === 'number' ? `${edge.weight.toFixed(1)}s` : '',
          color: edge.connector ? '#e74c3c' : '#4b5563',
        };
        if (edgesDataset.get(id)) {
          edgesDataset.update(payload);
        } else {
          edgesDataset.add(payload);
        }
        statusBox.textContent = `Edge ${edge.source} -> ${edge.target} updated.`;
      }

      async function loadModes() {
        const response = await fetch('/api/v1/transport/modes');
        const data = await response.json();
        modeSelect.innerHTML = '';
        data.modes.forEach((mode) => {
          const option = document.createElement('option');
          option.value = mode;
          option.textContent = mode;
          modeSelect.appendChild(option);
        });
        if (!selectedMode && data.modes.length > 0) {
          selectedMode = data.modes[0];
        }
        if (selectedMode) {
          modeSelect.value = selectedMode;
          edgeModeInput.value = selectedMode;
          await loadGraph(selectedMode);
        }
      }

      async function loadGraph(mode) {
        const response = await fetch(`/api/v1/transport/graphs?mode=${encodeURIComponent(mode)}`);
        const data = await response.json();
        const graph = data.graphs[mode];
        if (graph) {
          selectedMode = mode;
          edgeModeInput.value = mode;
          renderGraph(graph);
        }
      }

      function connectSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const streamPath = '/api/v1/transport/graphs/stream';
        const socketUrl = `${protocol}://${window.location.host}${streamPath}`;
        socket = new WebSocket(socketUrl);
        socket.onmessage = (event) => {
          const message = JSON.parse(event.data);
          if (message.type === 'snapshot') {
            const snapshot = message.graphs;
            if (selectedMode && snapshot[selectedMode]) {
              renderGraph(snapshot[selectedMode]);
            }
          }
          if (message.type === 'edge_updated') {
            applyEdgeUpdate(message.edge);
          }
        };
        socket.onclose = () => {
          statusBox.textContent = 'Disconnected from graph stream. Reconnecting…';
          setTimeout(connectSocket, 2000);
        };
      }

      document.getElementById('edgeForm').addEventListener('submit', async (event) => {
        event.preventDefault();
        const mode = edgeModeInput.value.trim();
        const source = document.getElementById('edgeSource').value.trim();
        const target = document.getElementById('edgeTarget').value.trim();
        const key = document.getElementById('edgeKey').value.trim();
        const weightRaw = document.getElementById('edgeWeight').value.trim();
        const speedRaw = document.getElementById('edgeSpeed').value.trim();
        const payload = {};
        if (key) payload.key = key;
        if (weightRaw) payload.weight = parseFloat(weightRaw);
        if (speedRaw) payload.speed_kmh = parseFloat(speedRaw);
        if (!payload.weight && !payload.speed_kmh) {
          statusBox.textContent = 'Provide at least weight or speed.';
          return;
        }
        const edgeEndpoint = `/api/v1/transport/graphs/${encodeURIComponent(mode)}/edges/${
          encodeURIComponent(source)
        }/${encodeURIComponent(target)}`;
        const response = await fetch(edgeEndpoint, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (response.ok) {
          const result = await response.json();
          statusBox.textContent = `Edge updated: ${JSON.stringify(result.edge)}`;
          await loadGraph(mode);
        } else {
          const error = await response.json();
          statusBox.textContent = `Update failed: ${error.detail}`;
        }
      });

      document.getElementById('nearestForm').addEventListener('submit', async (event) => {
        event.preventDefault();
        const payload = {
          latitude: parseFloat(document.getElementById('latitude').value),
          longitude: parseFloat(document.getElementById('longitude').value),
          weight: parseFloat(document.getElementById('nearestWeight').value),
        };
        const response = await fetch('/api/v1/transport/graphs/nearest', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (response.ok) {
          const result = await response.json();
          statusBox.textContent = `Nearest edge updated: ${JSON.stringify(result.edge)}`;
          if (result.edge.mode) {
            await loadGraph(result.edge.mode);
          }
        } else {
          const error = await response.json();
          statusBox.textContent = `Nearest update failed: ${error.detail}`;
        }
      });

      modeSelect.addEventListener('change', async (event) => {
        selectedMode = event.target.value;
        edgeModeInput.value = selectedMode;
        await loadGraph(selectedMode);
      });

      loadModes();
      connectSocket();
    </script>
  </body>
</html>
"""


@router.get(
    "/modes",
    response_model=AvailableModesResponse,
    summary="List transport modes",
)
async def list_transport_modes(
    service: TransportGraphService = Depends(get_transport_graph_service),
) -> AvailableModesResponse:
    """Return transport graph modes constructed during application startup."""

    modes = service.available_modes()
    return AvailableModesResponse(modes=modes)


@router.get(
    "/graphs",
    response_model=GraphSnapshotResponse,
    summary="Retrieve transport graph snapshot",
)
async def get_transport_graphs(
    mode: str | None = None,
    service: TransportGraphService = Depends(get_transport_graph_service),
) -> GraphSnapshotResponse:
    """Return serialized representations of the constructed transport graphs."""

    try:
        snapshot = service.graph_snapshot(mode=mode)
    except KeyError as exc:  # pragma: no cover - maps to HTTP error response
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return GraphSnapshotResponse(graphs=snapshot)


@router.get(
    "/routes",
    response_model=RoutePlanResponse,
    summary="Plan route with incident awareness",
)
async def plan_incident_aware_route(
    mode: str = Query(..., min_length=1, description="Transport mode to traverse."),
    source: str = Query(..., min_length=1, description="Identifier of the starting node."),
    target: str = Query(..., min_length=1, description="Identifier of the destination node."),
    service: TransportGraphService = Depends(get_transport_graph_service),
) -> RoutePlanResponse:
    """Return the default route and warn when incidents require an alternative."""

    try:
        payload = service.plan_route_with_incidents(mode=mode, source=source, target=target)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return RoutePlanResponse.model_validate(payload)


@router.patch(
    "/graphs/{mode}/edges/{source}/{target}",
    response_model=EdgeUpdateResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": EdgeErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": EdgeErrorResponse},
    },
    summary="Modify a transport graph edge",
)
async def update_transport_edge(
    mode: str,
    source: str,
    target: str,
    payload: EdgeUpdatePayload,
    service: TransportGraphService = Depends(get_transport_graph_service),
) -> EdgeUpdateResponse:
    """Update weight or speed metadata for an edge in the requested transport graph."""

    try:
        updated = service.update_edge(
            mode=mode,
            source=source,
            target=target,
            key=payload.key,
            weight=payload.weight,
            speed_kmh=payload.speed_kmh,
        )
    except KeyError as exc:  # pragma: no cover - control flow maps to HTTP error
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:  # pragma: no cover - control flow maps to HTTP error
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return EdgeUpdateResponse(edge=EdgeDetail(**updated))


@router.post(
    "/graphs/nearest/lookup",
    response_model=ClosestEdgeLookupResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": EdgeErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": EdgeErrorResponse},
    },
    summary="Find the nearest transit edge",
)
async def lookup_nearest_transit_edge(
    payload: ClosestEdgeLookupPayload,
    service: TransportGraphService = Depends(get_transport_graph_service),
) -> ClosestEdgeLookupResponse:
    """Return information about the closest non-walking/non-bike edge."""

    try:
        edge = service.get_closest_transit_edge(
            latitude=payload.latitude,
            longitude=payload.longitude,
        )
    except ValueError as exc:  # pragma: no cover - mapped to HTTP error
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ClosestEdgeLookupResponse(edge=EdgeDetail(**edge))


@router.patch(
    "/graphs/nearest",
    response_model=ClosestEdgeUpdateResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": EdgeErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": EdgeErrorResponse},
    },
    summary="Modify the nearest transit edge",
)
async def update_nearest_transit_edge(
    payload: ClosestEdgeUpdatePayload,
    service: TransportGraphService = Depends(get_transport_graph_service),
) -> ClosestEdgeUpdateResponse:
    """Update the closest non-walking/non-bike edge to supplied coordinates."""

    try:
        updated = service.update_closest_transit_edge(
            latitude=payload.latitude,
            longitude=payload.longitude,
            weight=payload.weight,
        )
    except ValueError as exc:  # pragma: no cover - mapped to HTTP error
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ClosestEdgeUpdateResponse(edge=EdgeDetail(**updated))


@router.websocket("/graphs/stream")
async def stream_transport_graph(
    websocket: WebSocket,
    service: TransportGraphService = Depends(get_transport_graph_service),
) -> None:
    """Expose a WebSocket that streams graph snapshots and incremental updates."""

    await websocket.accept()
    queue = service.subscribe()
    try:
        await websocket.send_json({"type": "snapshot", "graphs": service.graph_snapshot()})
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        service.unsubscribe(queue)


@router.get(
    "/visualizer",
    response_class=HTMLResponse,
    summary="Interactive transport graph visualizer",
)
async def transport_visualizer() -> HTMLResponse:
    """Serve a lightweight HTML interface for graph exploration and live updates."""

    return HTMLResponse(content=VISUALIZER_HTML)
