"""Every operation in contracts/api-examples.json (API-001..070) has a route with the same method and path."""
import re

from conftest import CONTRACTS

from app import main


def _normalize(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path)


def test_all_contract_operations_are_routed():
    routes = {(m, _normalize(r.path)) for router in main.ROUTERS for r in router.routes for m in r.methods}
    missing = [f"{c['id']} {c['method']} {c['path']}" for c in CONTRACTS.values() if (c["method"], _normalize(c["path"])) not in routes]
    assert len(CONTRACTS) == 70 and missing == []
