"""Graph memory: related items (API-068). Backed by ems.graph_neighbors() under RLS (DB-11)."""
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.graph import service as graph
from app.platform.context import SessionCtx
from app.platform.errors import ApiError, not_found
from app.platform.responses import ok

router = APIRouter(prefix="/api/v1/graph")


@router.get("/neighbors")
def neighbors(ctx: SessionCtx, kind: Literal["person", "client", "company", "contact", "deal", "project", "task", "invoice", "skill"],
              ref_id: uuid.UUID, depth: Annotated[int, Query()] = 1):
    if not 1 <= depth <= 3:
        raise ApiError("VALIDATION_FAILED", "Depth must be 1, 2 or 3.")
    node = graph.node_for(ctx.db, kind, ref_id)
    if node is None or not graph.can_read_kind(ctx, kind):
        raise not_found("Item")
    return ok({"node": {"kind": node["kind"], "ref_id": node["ref_id"], "label": node["label"]},
               "neighbors": graph.neighbors(ctx, node["id"], depth)})
