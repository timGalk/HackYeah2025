"""Minimal HTML admin panel for moderating incident records."""

from __future__ import annotations

import html
import logging
from datetime import datetime
from typing import Iterable

from fastapi import APIRouter, Body, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
from supabase import Client, create_client

from app.api.dependencies import get_facebook_post_service, get_incident_service
from app.schemas.facebook_posts import FacebookPostRead
from app.schemas.incidents import IncidentRead
from app.services.facebook_posts import FacebookPostService
from app.services.incidents import IncidentService

load_dotenv()
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)

logger = logging.getLogger(__name__)

class IncidentPurgeRequest(BaseModel):
    """Payload describing which incident records should be removed."""

    start: datetime | None = Field(
        default=None,
        description="Inclusive start of the interval to delete (ISO8601).",
    )
    end: datetime | None = Field(
        default=None,
        description="Inclusive end of the interval to delete (ISO8601).",
    )


class IncidentPurgeResponse(BaseModel):
    """Summary response returned after deleting incident records."""

    deleted: int = Field(..., ge=0, description="Number of records removed from the index.")
    scope: str = Field(..., description="Deletion scope identifier (all or range).")
    start: datetime | None = Field(default=None)
    end: datetime | None = Field(default=None)

router = APIRouter(prefix="/admin/incidents", tags=["admin"], include_in_schema=False)


@router.get("", response_class=HTMLResponse, name="admin_incidents_panel")
async def admin_incidents_panel(
    request: Request,
    incident_service: IncidentService = Depends(get_incident_service),
    post_service: FacebookPostService = Depends(get_facebook_post_service),
) -> HTMLResponse:
    """Render a simple HTML page showing incidents and Facebook posts for moderation."""

    incidents_response = await incident_service.get_all_incidents()
    posts_response = await post_service.list_posts()
    message = request.query_params.get("status")
    content = _render_panel(
        incidents=incidents_response.incidents,
        posts=posts_response.posts,
        heading="Incident and Facebook Post Approval Queue",
        status_message=_format_message(message),
    )
    return HTMLResponse(content=content)


@router.post("/{incident_id}/approve", name="approve_incident")
async def approve_incident(
    incident_id: str,
    service: IncidentService = Depends(get_incident_service),
) -> RedirectResponse:
    """Approve an incident and redirect back to the admin panel."""

    # Get incident details to retrieve the username
    all_incidents = await service.get_all_incidents()
    incident = next((inc for inc in all_incidents.incidents if inc.id == incident_id), None)
    
    # If incident found and has a username, try to increment user credits
    if incident and incident.username:
        try:
            # Query users table to find matching name
            users_response = supabase.table("users").select("*").eq("name", incident.username).execute()
            
            if users_response.data and len(users_response.data) > 0:
                user = users_response.data[0]
                user_id = user.get("id")
                current_credits = user.get("credit", 0)
                
                # Increment credits by 5
                new_credits = current_credits + 5
                supabase.table("users").update({"credit": new_credits}).eq("id", user_id).execute()
                logger.info(
                    f"Incremented credits for user {incident.username} "
                    f"(id: {user_id}) from {current_credits} to {new_credits}"
                )
        except Exception as e:
            # Log the error but continue with incident approval
            logger.error(f"Error updating user credits for {incident.username}: {e}")
    
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


@router.post("/posts/{post_id}/approve", name="approve_facebook_post")
async def approve_facebook_post(
    post_id: str,
    service: FacebookPostService = Depends(get_facebook_post_service),
) -> RedirectResponse:
    """Approve a Facebook post and apply its transport impact."""

    post = await service.get_post(post_id)
    if post is None:
        status_fragment = "post_not_found"
    else:
        success = await service.approve_post(post_id)
        status_fragment = "post_approved" if success else "post_error"
    redirect_target = router.url_path_for("admin_incidents_panel") + f"?status={status_fragment}"
    return RedirectResponse(url=redirect_target, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/posts/{post_id}/revoke", name="revoke_facebook_post")
async def revoke_facebook_post(
    post_id: str,
    service: FacebookPostService = Depends(get_facebook_post_service),
) -> RedirectResponse:
    """Revoke approval for a Facebook post and revert its transport impact."""

    post = await service.get_post(post_id)
    if post is None:
        status_fragment = "post_not_found"
    else:
        success = await service.revoke_post(post_id)
        status_fragment = "post_revoked" if success else "post_error"
    redirect_target = router.url_path_for("admin_incidents_panel") + f"?status={status_fragment}"
    return RedirectResponse(url=redirect_target, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/purge", name="purge_incidents")
async def purge_incidents(
    start: str | None = Form(None),
    end: str | None = Form(None),
    clear_all: str | None = Form(None),
    service: IncidentService = Depends(get_incident_service),
) -> RedirectResponse:
    """Delete incidents matching the optional time window and redirect back."""

    status_fragment = "purged"
    try:
        if clear_all:
            deleted = await service.delete_incidents_all()
            status_fragment = f"purged_{deleted}"
        elif start and end:
            start_dt = _parse_datetime(start)
            end_dt = _parse_datetime(end)
            deleted = await service.delete_incidents_in_range(start=start_dt, end=end_dt)
            status_fragment = f"purged_{deleted}"
        elif start or end:
            raise ValueError("Both 'start' and 'end' must be provided for ranged purge.")
        else:
            raise ValueError("Provide both 'start' and 'end' or use the 'Delete all' button.")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    redirect_target = router.url_path_for("admin_incidents_panel") + f"?status={status_fragment}"
    return RedirectResponse(url=redirect_target, status_code=status.HTTP_303_SEE_OTHER)


@router.delete("/api", include_in_schema=True, response_model=IncidentPurgeResponse, status_code=status.HTTP_200_OK)
async def purge_incidents_api(
    payload: IncidentPurgeRequest = Body(default_factory=IncidentPurgeRequest),
    service: IncidentService = Depends(get_incident_service),
) -> IncidentPurgeResponse:
    """Programmatic endpoint for deleting incidents by range or entirely."""

    if payload.start and payload.end:
        deleted = await service.delete_incidents_in_range(start=payload.start, end=payload.end)
        scope = "range"
    elif payload.start or payload.end:
        msg = "Both 'start' and 'end' must be provided to delete by range."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    else:
        deleted = await service.delete_incidents_all()
        scope = "all"

    return IncidentPurgeResponse(
        deleted=deleted,
        scope=scope,
        start=payload.start,
        end=payload.end,
    )


def _render_panel(
    *,
    incidents: Iterable[IncidentRead],
    posts: Iterable[FacebookPostRead],
    heading: str,
    status_message: str | None,
) -> str:
    """Build a lightweight HTML page for moderating incidents and Facebook posts."""

    incident_rows = "".join(_render_incident_row(incident=incident) for incident in incidents)
    if not incident_rows:
        incident_rows = "<tr><td colspan=7>No incidents recorded yet.</td></tr>"

    post_rows = "".join(_render_post_row(post=post) for post in posts)
    if not post_rows:
        post_rows = "<tr><td colspan=8>No Facebook posts ingested yet.</td></tr>"

    status_block = f"<p class='status'>{html.escape(status_message)}</p>" if status_message else ""

    return (
        "<!DOCTYPE html>"
        "<html lang='en'>"
        "<head>"
        "<meta charset='utf-8'>"
        f"<title>{html.escape(heading)}</title>"
        "<style>"
        "body{font-family:Arial,sans-serif;margin:2rem;}"
        "table{border-collapse:collapse;width:100%;margin-top:1rem;}"
        "th,td{border:1px solid #ccc;padding:0.5rem;text-align:left;}"
        "th{background:#f0f0f0;}"
        ".actions{display:flex;gap:0.5rem;}"
        ".status{margin-bottom:1rem;color:#064420;font-weight:bold;}"
        "form.inline{display:flex;gap:0.5rem;align-items:center;}"
        "fieldset{border:1px solid #ccc;padding:1rem;}legend{font-weight:bold;}"
        "section{margin-top:2rem;}"
        "</style>"
        "</head>"
        "<body>"
        f"<h1>{html.escape(heading)}</h1>"
        f"{status_block}"
        f"{_render_purge_form()}"
        "<section>"
        "<h2>Incidents</h2>"
        "<table>"
        "<thead><tr>"
        "<th>ID</th><th>Category</th><th>Description</th><th>User</th>"
        "<th>Score</th><th>Status</th><th>Actions</th>"
        "</tr></thead>"
        f"<tbody>{incident_rows}</tbody>"
        "</table>"
        "</section>"
        "<section>"
        "<h2>Facebook Posts</h2>"
        "<table>"
        "<thead><tr>"
        "<th>ID</th><th>Description</th><th>Category</th><th>Stop</th>"
        "<th>Coordinates</th><th>Status</th><th>Edge</th><th>Actions</th>"
        "</tr></thead>"
        f"<tbody>{post_rows}</tbody>"
        "</table>"
        "</section>"
        "</body>"
        "</html>"
    )


def _render_incident_row(*, incident: IncidentRead) -> str:
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


def _render_post_row(*, post: FacebookPostRead) -> str:
    """Render a table row representing a single Facebook post."""

    description = (post.description[:140] + "...") if len(post.description) > 140 else post.description
    approve_url = router.url_path_for("approve_facebook_post", post_id=post.id)
    revoke_url = router.url_path_for("revoke_facebook_post", post_id=post.id)
    is_approved = bool(post.approved)
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

    coordinates = f"{post.latitude:.5f}, {post.longitude:.5f}"
    edge_mode = post.edge_mode or "-"
    edge_key = str(post.edge_key) if post.edge_key is not None else "-"
    edge_label = f"{html.escape(edge_mode)}/{html.escape(edge_key)}"

    return (
        "<tr>"
        f"<td>{html.escape(post.id)}</td>"
        f"<td>{html.escape(description)}</td>"
        f"<td>{html.escape(post.category)}</td>"
        f"<td>{html.escape(post.stop_name or '-')}</td>"
        f"<td>{coordinates}</td>"
        f"<td>{status_label}</td>"
        f"<td>{edge_label}</td>"
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
    if status_token == "post_approved":
        return "Facebook post approved and applied to the network."
    if status_token == "post_revoked":
        return "Facebook post approval revoked."
    if status_token == "post_not_found":
        return "Facebook post not found."
    if status_token == "post_error":
        return "Unable to apply the Facebook post impact. Check server logs for details."
    if status_token and status_token.startswith("purged_"):
        count = status_token.split("_", 1)[1]
        return f"Deleted {count} incident(s)."
    return None


def _render_purge_form() -> str:
    """Render a simple form for purging incidents by time interval."""

    return (
        "<form class='inline' method='post' action='purge'>"
        "<fieldset>"
        "<legend>Delete incidents</legend>"
        "<label>Start (ISO8601): <input type='datetime-local' name='start'></label>"
        "<label>End (ISO8601): <input type='datetime-local' name='end'></label>"
        "<button type='submit'>Delete range</button>"
        "<button type='submit' name='clear_all' value='1'>Delete all</button>"
        "</fieldset>"
        "</form>"
    )


def _parse_datetime(value: str) -> datetime:
    """Parse ISO8601 datetime strings provided via the admin form."""

    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        msg = "Date-time values must be ISO8601 formatted."
        raise ValueError(msg) from exc
