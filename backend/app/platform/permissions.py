"""Role permission matrix (spec Section 7.2, DEC-009). Used by `require()` and returned by API-009 / API-016."""
ROLES = ("ceo", "cto", "cfo", "coo", "hr", "manager", "employee")
LEADERSHIP = frozenset({"ceo", "cto", "cfo", "coo"})
ALL, TEAM = "all", "team"

# permission -> {role: scope}. "team" means the manager's direct reports only.
MATRIX: dict[str, dict[str, str]] = {
    "room.view_live": {"ceo": ALL, "coo": ALL},
    "room.self": {r: ALL for r in ROLES},
    "hr.manage": {"ceo": ALL, "coo": ALL, "hr": ALL, "manager": TEAM},
    "leave.decide": {"ceo": ALL, "hr": ALL, "manager": TEAM},
    "projects.manage": {"ceo": ALL, "cto": ALL, "coo": ALL, "manager": ALL},
    "crm.manage": {"ceo": ALL, "coo": ALL, "manager": ALL},
    "finance.manage": {"ceo": ALL, "cfo": ALL},
    "hunter.use": {"ceo": ALL, "coo": ALL, "manager": ALL},
    "rules.manage": {"ceo": ALL, "cto": ALL, "coo": ALL},
    "members.manage": {"ceo": ALL, "hr": ALL},
    "leakage.read": {"ceo": ALL, "cfo": ALL, "coo": ALL},
    "leakage.resolve": {"ceo": ALL, "cfo": ALL},
    "dashboards.all": {"ceo": ALL},
}

DASHBOARD_FOR_ROLE = {"ceo": "ceo", "cto": "cto", "cfo": "cfo", "coo": "coo", "hr": "hr", "manager": "employee", "employee": "employee"}


def scope(role: str, permission: str) -> str | None:
    return MATRIX[permission].get(role)


def permissions_for(role: str) -> list[str]:
    return [p for p, roles in MATRIX.items() if role in roles]


def roles_with(permission: str) -> list[str]:
    return [r for r in ROLES if r in MATRIX[permission]]
