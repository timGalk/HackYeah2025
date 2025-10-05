"""Minimal HTML admin panel for moderating incident approvals."""

from __future__ import annotations

import html
from typing import Iterable

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.dependencies import get_incident_service
from app.schemas.incidents import IncidentRead
from app.services.incidents import IncidentService

router = APIRouter(prefix="/admin/incidents", tags=["admin"], include_in_schema=False)


@router.get("", response_class=HTMLResponse, name="admin_incidents_panel")
async def admin_incidents_panel(
    request: Request,
    service: IncidentService = Depends(get_incident_service),
) -> HTMLResponse:
    """Render a simple HTML page showing incidents and their approval state."""

    response = await service.get_all_incidents()
    message = request.query_params.get("status")
    content = _render_panel(
        incidents=response.incidents,
        heading="Incident Approval Queue",
        status_message=_format_message(message),
    )
    return HTMLResponse(content=content)


@router.post("/{incident_id}/approve", name="approve_incident")
async def approve_incident(
    incident_id: str,
    service: IncidentService = Depends(get_incident_service),
) -> RedirectResponse:
    """Approve an incident and redirect back to the admin panel."""

    success = await service.approve_incident(incident_id)
    status_fragment = "approved" if success else "not_found"
    redirect_target = router.url_path_for("admin_incidents_panel") + f"?status={status_fragment}"
    return RedirectResponse(url=redirect_target, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{incident_id}/revoke", name="revoke_incident")
async def revoke_incident(
    incident_id: str,
    service: IncidentService = Depends(get_incident_service),
) -> RedirectResponse:
    """Revoke incident approval and redirect back to the admin panel."""

    success = await service.revoke_incident_approval(incident_id)
    status_fragment = "revoked" if success else "not_found"
    redirect_target = router.url_path_for("admin_incidents_panel") + f"?status={status_fragment}"
    return RedirectResponse(url=redirect_target, status_code=status.HTTP_303_SEE_OTHER)


def _render_panel(
    *,
    incidents: Iterable[IncidentRead],
    heading: str,
    status_message: str | None,
) -> str:
    """Build a lightweight HTML page for the incident approval queue."""

    rows = "".join(_render_row(incident=incident) for incident in incidents)
    if not rows:
        rows = "<tr><td colspan=7>No incidents recorded yet.</td></tr>"

    status_block = f"<p class='status'>{html.escape(status_message)}</p>" if status_message else ""

    return (
        "<!DOCTYPE html>"
        "<html lang='en'>"
        "<head>"
        "<meta charset='utf-8'>"
        f"<title>{html.escape(heading)}</title>"
        "<style>"
        "body{font-family:Arial,sans-serif;margin:2rem;}"
        "table{border-collapse:collapse;width:100%;}"
        "th,td{border:1px solid #ccc;padding:0.5rem;text-align:left;}"
        "th{background:#f0f0f0;}"
        ".actions{display:flex;gap:0.5rem;}"
        ".status{margin-bottom:1rem;color:#064420;font-weight:bold;}"
        "</style>"
        "</head>"
        "<body>"
        f"<h1>{html.escape(heading)}</h1>"
        f"{status_block}"
        "<table>"
        "<thead><tr>"
        "<th>ID</th><th>Category</th><th>Description</th><th>User</th><th>Score</th><th>Status</th><th>Actions</th>"
        "</tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
        "</body>"
        "</html>"
    )


def _render_row(*, incident: IncidentRead) -> str:
    """Render a table row representing a single incident."""

    description = (incident.description[:140] + "...") if len(incident.description) > 140 else incident.description
    approve_url = router.url_path_for("approve_incident", incident_id=incident.id)
    revoke_url = router.url_path_for("revoke_incident", incident_id=incident.id)
    is_approved = bool(incident.approved)
    status_label = "Approved" if is_approved else "Pending"
    action_button = (
        f"<form method='post' action='{html.escape(revoke_url)}'>"
        "<button type='submit'>Revoke approval</button>"
        "</form>"
        if is_approved
        else
        f"<form method='post' action='{html.escape(approve_url)}'>"
        "<button type='submit'>Approve</button>"
        "</form>"
    )
    return (
        "<tr>"
        f"<td>{html.escape(incident.id)}</td>"
        f"<td>{html.escape(incident.category)}</td>"
        f"<td>{html.escape(description)}</td>"
        f"<td>{html.escape(incident.username)}</td>"
        f"<td>{incident.reporter_social_score:.2f}</td>"
        f"<td>{status_label}</td>"
        f"<td class='actions'>{action_button}</td>"
        "</tr>"
    )


def _format_message(status_token: str | None) -> str | None:
    """Translate a status token into a human-readable message."""

    if status_token == "approved":
        return "Incident approved successfully."
    if status_token == "revoked":
        return "Incident approval revoked."
    if status_token == "not_found":
        return "Incident not found or already in the requested state."
    return None
