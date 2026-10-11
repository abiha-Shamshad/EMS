"""Graph memory in PostgreSQL (spec Section 16, DEC-008): graph_nodes / graph_edges, traversal by ems.graph_neighbors().

Edges carry valid_from / valid_to: a change closes the old edge and opens a new one, so history is kept.
Writers are called from worker event handlers and must be idempotent (Section 31.2).
"""
import uuid
from typing import Any

from app.platform.db import Db

# Which permission lets a caller see a node of each kind in "Related" panels (API-068: filtered by read permissions).
KIND_READ = {"person": None, "skill": None,
             "project": ("projects.manage", "crm.manage", "finance.manage"), "task": ("projects.manage",),
             "client": ("crm.manage", "finance.manage", "cfo"), "company": ("crm.manage", "cfo"),
             "contact": ("crm.manage", "cfo"), "deal": ("crm.manage", "cfo"), "invoice": ("finance.manage",)}


def ensure_node(db: Db, org_id: Any, kind: str, ref_id: Any, label: str) -> uuid.UUID:
    return db.scalar("INSERT INTO ems.graph_nodes (id, org_id, kind, ref_id, label) VALUES (:id, :org, :k, :r, :l) "
                     "ON CONFLICT (org_id, kind, ref_id) DO UPDATE SET label = EXCLUDED.label RETURNING id",
                     id=uuid.uuid4(), org=org_id, k=kind, r=ref_id, l=(label or kind)[:200])


def link(db: Db, org_id: Any, src: uuid.UUID, dst: uuid.UUID, kind: str, evidence: str) -> None:
    """Open a current edge unless one already exists (ux_edge_current)."""
    if src == dst:
        return
    db.execute("INSERT INTO ems.graph_edges (id, org_id, src, dst, kind, evidence) VALUES (:id, :org, :s, :d, :k, :e) "
               "ON CONFLICT (org_id, src, dst, kind) WHERE valid_to IS NULL DO NOTHING",
               id=uuid.uuid4(), org=org_id, s=src, d=dst, k=kind, e=evidence[:200])


def relink(db: Db, org_id: Any, src: uuid.UUID, kind: str, dst: uuid.UUID | None, evidence: str) -> None:
    """Single-valued relation (reports_to, owns of one record...): close edges to other targets, open the new one."""
    db.execute("UPDATE ems.graph_edges SET valid_to = now() WHERE src = :s AND kind = :k AND valid_to IS NULL "
               "AND (CAST(:d AS uuid) IS NULL OR dst <> :d)", s=src, k=kind, d=dst)
    if dst is not None:
        link(db, org_id, src, dst, kind, evidence)


def relink_incoming(db: Db, org_id: Any, dst: uuid.UUID, kind: str, src: uuid.UUID | None, evidence: str) -> None:
    """Single-valued incoming relation, e.g. the one owner of a deal: person -owns-> deal."""
    db.execute("UPDATE ems.graph_edges SET valid_to = now() WHERE dst = :d AND kind = :k AND valid_to IS NULL "
               "AND (CAST(:s AS uuid) IS NULL OR src <> :s)", d=dst, k=kind, s=src)
    if src is not None:
        link(db, org_id, src, dst, kind, evidence)


def node_for(db: Db, kind: str, ref_id: Any) -> dict[str, Any] | None:
    return db.one("SELECT id, kind, ref_id, label FROM ems.graph_nodes WHERE kind = :k AND ref_id = :r", k=kind, r=ref_id)


def can_read_kind(ctx, kind: str) -> bool:
    needs = KIND_READ.get(kind)
    return needs is None or any(ctx.role == n if n == "cfo" else ctx.can(n) for n in needs)


def neighbors(ctx, node_id: uuid.UUID, depth: int) -> list[dict[str, Any]]:
    rows = ctx.db.all("SELECT n.node_id, n.kind, n.label, n.depth, n.path_kinds, g.ref_id "
                      "FROM ems.graph_neighbors(:n, :d) n JOIN ems.graph_nodes g ON g.id = n.node_id ORDER BY n.depth, n.label",
                      n=node_id, d=depth)
    return [{"kind": r["kind"], "ref_id": r["ref_id"], "label": r["label"], "depth": r["depth"], "via": list(r["path_kinds"])}
            for r in rows if can_read_kind(ctx, r["kind"])]
