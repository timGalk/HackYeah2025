"""Admin-facing routes for manual moderation tasks."""

from app.api.admin.incidents import router as incidents_admin_router

__all__ = ["incidents_admin_router"]
