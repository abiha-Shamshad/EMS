#!/usr/bin/env python3
"""EMS Release 1 endpoint registry, contracts and examples (request, success result, error result).
Usage: python3 gen_api.py <first_section_number> <out.md> <out.json>"""
import json, re, sys, uuid

NS = uuid.UUID("6f1c2a52-3c8e-4f0e-9a51-0d2b7c4e9a10")
def I(name):  # deterministic synthetic UUID for fixture objects
    return str(uuid.uuid5(NS, name))

RID = "req_7f3a9c21"
def ok(data, ts, msg=None):
    d = {"success": True}
    if msg:
        d["message"] = msg
    d["data"] = data
    d["meta"] = {"api_version": "v1", "request_id": RID, "timestamp": ts}
    return d

def err(code, message, retryable=False, details=None):
    return {"success": False, "error": {"code": code, "message": message, "retryable": retryable, "details": details or {}},
            "meta": {"api_version": "v1", "request_id": RID}}

S = "Session cookie `ems_session` (HttpOnly, Secure, SameSite=Lax) + `X-CSRF-Token` on unsafe methods; `X-Org-Id` when the user has several companies"
SR = "Session cookie `ems_session`; `X-Org-Id` when the user has several companies"
EXT = "Extension bearer token `Authorization: Bearer <ext token>` issued by API-018"
T0 = "2026-10-12T04:02:00Z"   # Monday 12 Oct 2026, 09:02 PKT (Asia/Karachi, UTC+5)

E = []
def ep(**k):
    k.setdefault("extra", [])
    k.setdefault("req", None)
    E.append(k)

CEO = {"user_id": I("u-ceo"), "name": "Imran Qureshi", "role": "ceo"}
BILAL = {"user_id": I("u-bilal"), "name": "Bilal Ahmed", "role": "employee"}

# ===================================================================== System and authentication
ep(d="System and Authentication", m="GET", p="/health", t="Health and readiness", auth="public (private network for details)",
   purpose="Load balancer readiness; 200 when PostgreSQL is reachable, body reports degraded dependencies.",
   perm="None", params="None", idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res={"status": "ready", "checks": {"postgres": "ok", "livekit": "ok", "worker_lag_seconds": 2}, "version": "1.0.0"},
   extra=[("Degraded but serving (media server down)", 200, {"status": "degraded", "checks": {"postgres": "ok", "livekit": "unavailable", "worker_lag_seconds": 3}, "version": "1.0.0"})],
   ecode=503, eres={"status": "unavailable", "checks": {"postgres": "unavailable"}, "version": "1.0.0"},
   errs=[(200, "Ready or degraded"), (503, "PostgreSQL unreachable")],
   rules=["Live streaming outage never removes API instances; the Room shows streams as unavailable and keeps presence working."])

ep(d="System and Authentication", m="POST", p="/api/v1/auth/signup", t="Create company account", auth="public",
   purpose="Screen 'Create Company Account': creates the user, the company and the CEO membership in one transaction, then signs in.",
   perm="Public; rate limited 5 per hour per IP", params="None", idem="Idempotency-Key required (client-generated UUID).",
   audit="org.created, user.created", event="org.created", worker="Verification email (INT-003; until then the account is usable and the banner asks to verify).",
   req={"company_name": "Acme Tech", "company_slug": "acme-tech", "country": "PK", "time_zone": "Asia/Karachi",
        "name": "Imran Qureshi", "email": "imran@acmetech.example", "password": "correct-horse-battery-staple-42"},
   code=201, res=ok({"user": {"id": CEO["user_id"], "name": "Imran Qureshi", "email": "imran@acmetech.example"},
                     "org": {"id": I("org-acme"), "name": "Acme Tech", "slug": "acme-tech", "setup_state": "account_created"},
                     "membership": {"role": "ceo"}, "next_step": "company_setup"}, "2026-10-01T05:00:00Z", "Company account created."),
   ecode=409, eres=err("SLUG_TAKEN", "That company address is already taken. Try another.", details={"field": "company_slug"}),
   errs=[(201, "Created and signed in (Set-Cookie)"), (400, "VALIDATION_FAILED - weak password (< 12 chars) or bad email"), (409, "SLUG_TAKEN or EMAIL_IN_USE"), (429, "RATE_LIMITED")],
   rules=["Password: 12-128 characters, checked against a local list of common passwords; stored as argon2id (argon2-cffi 25.1.0).",
          "Uses `ems.signup_company()` because no organization context exists yet (verified, DB-03/DB-05)."])

ep(d="System and Authentication", m="POST", p="/api/v1/auth/login", t="Sign in with email and password", auth="public",
   purpose="Screen 01 Login: verify credentials and create a session; 'Keep me signed in' extends it to 30 days.",
   perm="Public; 10 attempts per 15 min per email + IP", params="None", idem="Not idempotent; each success creates a session.",
   audit="auth.login_succeeded / auth.login_failed (no password)", event="None.", worker="None.",
   req={"email": "imran@acmetech.example", "password": "correct-horse-battery-staple-42", "remember": True},
   code=200, res=ok({"user": {"id": CEO["user_id"], "name": "Imran Qureshi"}, "session_expires_at": "2026-11-11T04:00:00Z",
                     "organizations": [{"id": I("org-acme"), "name": "Acme Tech", "role": "ceo"}], "redirect": "/dashboards/ceo"}, "2026-10-12T04:00:00Z", "Signed in."),
   ecode=401, eres=err("INVALID_CREDENTIALS", "Email or password is incorrect."),
   errs=[(200, "Signed in (Set-Cookie ems_session)"), (401, "INVALID_CREDENTIALS (same message for unknown email)"), (429, "RATE_LIMITED")],
   rules=["Session token: 32 random bytes; only its SHA-256 is stored (`ems.create_session`).",
          "Unknown email and wrong password return the same error and take similar time (dummy argon2 verify)."])

ep(d="System and Authentication", m="POST", p="/api/v1/auth/logout", t="Sign out", auth="session",
   purpose="Revoke the current session.", perm="Signed-in user", params="None", idem="Idempotent.",
   audit="auth.logout", event="None.", worker="None.", req={},
   code=200, res=ok({"signed_out": True}, "2026-10-12T13:00:00Z"),
   ecode=401, eres=err("AUTHENTICATION_REQUIRED", "You are not signed in."),
   errs=[(200, "Signed out (cookie cleared)"), (401, "No session")], rules=["Revocation is immediate (`ems.revoke_session`, DB-04)."])

ep(d="System and Authentication", m="POST", p="/api/v1/auth/password/forgot", t="Request password reset", auth="public",
   purpose="Send a reset link if the email exists; the response never reveals whether it does.",
   perm="Public; 3 per hour per email", params="None", idem="Repeated requests replace the previous token.",
   audit="auth.reset_requested", event="None.", worker="Reset email (INT-003).", req={"email": "imran@acmetech.example"},
   code=202, res=ok({"accepted": True}, "2026-10-12T04:00:00Z", "If that email has an account, a reset link is on its way."),
   ecode=429, eres=err("RATE_LIMITED", "Too many requests. Try again later.", True),
   errs=[(202, "Accepted (always, for known and unknown emails)"), (429, "RATE_LIMITED")],
   rules=["Token valid 30 minutes, single use, stored hashed. Blocked until INT-003 email is available; the UI shows 'Contact your company admin' meanwhile."])

ep(d="System and Authentication", m="POST", p="/api/v1/auth/password/reset", t="Reset password", auth="public",
   purpose="Set a new password with a reset token; revokes all existing sessions.",
   perm="Valid reset token", params="None", idem="Token single-use.", audit="auth.password_reset", event="None.", worker="None.",
   req={"token": "rst_redacted_example", "new_password": "a-new-long-passphrase-2026"},
   code=200, res=ok({"password_changed": True, "sessions_revoked": 2}, "2026-10-12T04:10:00Z", "Password changed. Sign in again."),
   ecode=410, eres=err("RESET_TOKEN_EXPIRED", "This reset link has expired. Request a new one."),
   errs=[(200, "Changed"), (400, "VALIDATION_FAILED - weak password"), (410, "RESET_TOKEN_EXPIRED or already used")], rules=["All sessions of the user are revoked in the same transaction."])

ep(d="System and Authentication", m="GET", p="/api/v1/auth/google/start", t="Start Google sign-in", auth="public",
   purpose="'Continue with Google': redirect to Google's authorization endpoint with state and nonce.",
   perm="Public", params="return_to (relative path, optional)", idem="Each call creates a new state value.", audit="None.", event="None.", worker="None.",
   code=302, res={"status": 302, "location": "https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id=<GOOGLE_CLIENT_ID>&scope=openid%20email%20profile&redirect_uri=https%3A%2F%2Fapp.ems.example%2Fapi%2Fv1%2Fauth%2Fgoogle%2Fcallback&state=<random>&nonce=<random>&code_challenge=<S256>&code_challenge_method=S256",
                  "set_cookie": "ems_oauth=<signed state+nonce+verifier>; HttpOnly; Secure; SameSite=Lax; Max-Age=600"},
   ecode=503, eres=err("GOOGLE_NOT_CONFIGURED", "Google sign-in is not available. Use email and password."),
   errs=[(302, "Redirect to Google"), (503, "GOOGLE_NOT_CONFIGURED")],
   rules=["Endpoints come from https://accounts.google.com/.well-known/openid-configuration (EV-006), cached per HTTP headers.",
          "INTEGRATION STATUS: READY TO IMPLEMENT (documented); sandbox test in TASK-004 needs the Google OAuth client (OD-07)."])

ep(d="System and Authentication", m="GET", p="/api/v1/auth/google/callback", t="Complete Google sign-in", auth="public",
   purpose="Exchange the code, validate the ID token, then sign in an existing user or attach Google to a matching invited email.",
   perm="Valid state cookie", params="code, state (query, from Google)", idem="Code is single-use at Google.", audit="auth.login_succeeded (method google)", event="None.", worker="None.",
   code=302, res={"status": 302, "location": "/dashboards/ceo", "set_cookie": "ems_session=<token>; HttpOnly; Secure; SameSite=Lax"},
   ecode=403, eres=err("GOOGLE_ACCOUNT_NOT_LINKED", "No EMS account uses this Google account. Ask your company admin for an invitation."),
   errs=[(302, "Signed in, redirect"), (400, "STATE_MISMATCH"), (403, "GOOGLE_ACCOUNT_NOT_LINKED")],
   rules=["Validate signature (jwks_uri), iss in {https://accounts.google.com, accounts.google.com}, aud = client ID, exp, nonce; identify users by `sub`, never by email (EV-006).",
          "Link Google to an existing user only when `email_verified` is true and the email matches a pending invitation or the signed-in user."])

ep(d="System and Authentication", m="GET", p="/api/v1/me", t="Current user, companies and permissions", auth="session",
   purpose="Drives navigation: role, permissions and setup state.", perm="Signed-in user", params="None", idem="Read-only.",
   audit="None.", event="None.", worker="None.",
   code=200, res=ok({"user": {"id": CEO["user_id"], "name": "Imran Qureshi", "email": "imran@acmetech.example"},
                     "active_org": {"id": I("org-acme"), "name": "Acme Tech", "role": "ceo", "time_zone": "Asia/Karachi", "setup_state": "active"},
                     "permissions": ["room.view_live", "room.self", "hr.manage", "leave.decide", "projects.manage", "crm.manage", "finance.manage",
                                     "hunter.use", "rules.manage", "members.manage", "leakage.read", "leakage.resolve", "dashboards.all"],
                     "dashboard": "ceo"}, "2026-10-12T04:00:05Z"),
   ecode=401, eres=err("AUTHENTICATION_REQUIRED", "Your session has expired. Sign in again."),
   errs=[(200, "Success"), (401, "No or expired session")], rules=["Permissions come from the role matrix (Section 7.2); the UI hides what is not listed, the API enforces it."])

# ===================================================================== Company and team
ep(d="Company and Team", m="PATCH", p="/api/v1/org", t="Company setup", auth="session",
   purpose="Screen 'Company Setup': industry, size, time zone, working hours.", perm="members.manage (CEO, HR)", params="None",
   idem="expected_version required.", audit="org.updated (field names)", event="org.updated", worker="None.",
   req={"expected_version": 1, "industry": "Software services", "size_band": "11-50", "time_zone": "Asia/Karachi",
        "work_hours": {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "09:00", "end": "18:00", "late_grace_minutes": 10}},
   code=200, res=ok({"id": I("org-acme"), "setup_state": "company_setup_done", "version": 2, "next_step": "invite_team"}, "2026-10-01T05:05:00Z", "Company details saved."),
   ecode=409, eres=err("VERSION_CONFLICT", "Company settings were changed by someone else. Reload and try again.", details={"current_version": 2}),
   errs=[(200, "Saved"), (400, "VALIDATION_FAILED"), (403, "AUTHORIZATION_DENIED"), (409, "VERSION_CONFLICT")], rules=["Working hours drive lateness and attendance (Section 10).", "Invite screen 'Skip for now' and the first accepted invitation both set `setup_state` to `active` (send `{\"expected_version\": n, \"setup_state\": \"active\"}`)."])

ep(d="Company and Team", m="POST", p="/api/v1/invitations", t="Invite team members", auth="session",
   purpose="Screen 06 Invite: up to 20 emails with roles and an optional message (max 300 characters).", perm="members.manage", params="None",
   idem="Idempotency-Key required; an email with a pending invitation is returned as `already_invited`.", audit="member.invited", event="member.invited", worker="Invitation email (INT-003); until then the response includes copyable links for the inviter.",
   req={"invites": [{"email": "bilal@acmetech.example", "role": "employee"}, {"email": "hina@acmetech.example", "role": "hr"}],
        "message": "Hi! Join our company workspace on EMS to collaborate with the team."},
   code=201, res=ok({"results": [{"email": "bilal@acmetech.example", "status": "invited", "invitation_id": I("inv-bilal"), "expires_at": "2026-10-08T05:10:00Z"},
                                 {"email": "hina@acmetech.example", "status": "invited", "invitation_id": I("inv-hina"), "expires_at": "2026-10-08T05:10:00Z"}],
                     "email_delivery": "not_configured", "copy_links": True, "org_setup_state": "team_invited"}, "2026-10-01T05:10:00Z", "2 invitations created."),
   ecode=400, eres=err("VALIDATION_FAILED", "Check the highlighted rows.", details={"fields": {"invites[1].role": "Role 'ceo' cannot be invited; there is one CEO per company."}}),
   errs=[(201, "Created (per-row results)"), (400, "VALIDATION_FAILED"), (403, "AUTHORIZATION_DENIED")],
   rules=["Allowed invite roles: cto, cfo, coo, hr, manager, employee (schema CHECK). The design's role list (Employee, HR, Manager) is a subset.",
          "Tokens: 32 random bytes, stored hashed, valid 7 days, single use."])

ep(d="Company and Team", m="POST", p="/api/v1/invitations/accept", t="Accept invitation", auth="session (new or existing user)",
   purpose="Join a company. New users set name and password in the same call.", perm="Holder of the token whose email matches", params="None",
   idem="Token single-use (DB-05).", audit="member.joined", event="member.joined", worker="None.",
   req={"token": "inv_redacted_example", "name": "Bilal Ahmed", "password": "bilal-long-passphrase-01"},
   code=200, res=ok({"org": {"id": I("org-acme"), "name": "Acme Tech"}, "membership": {"role": "employee"}, "next_step": "install_extension"}, "2026-10-02T06:00:00Z", "Welcome to Acme Tech."),
   ecode=403, eres=err("INVITATION_EMAIL_MISMATCH", "This invitation was sent to a different email address."),
   errs=[(200, "Joined"), (403, "INVITATION_EMAIL_MISMATCH"), (410, "INVITATION_INVALID (expired, used or revoked)")], rules=["Implemented by `ems.accept_invitation()` (DB-05)."])

ep(d="Company and Team", m="GET", p="/api/v1/members", t="List members", auth="session",
   purpose="Directory used by HR, assignment pickers and the Room.", perm="Any member (cost rates only for finance.manage)", params="role, status, department, cursor, limit",
   idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res=ok({"items": [{"user_id": CEO["user_id"], "name": "Imran Qureshi", "role": "ceo", "title": "Chief Executive", "department": "Leadership", "status": "active"},
                               {"user_id": BILAL["user_id"], "name": "Bilal Ahmed", "role": "employee", "title": "Backend Developer", "department": "Engineering", "status": "active", "manager_id": I("u-usman")}],
                     "next_cursor": None}, "2026-10-12T04:05:00Z"),
   ecode=401, eres=err("AUTHENTICATION_REQUIRED", "Your session has expired. Sign in again."),
   errs=[(200, "Success"), (401, "AUTHENTICATION_REQUIRED")], rules=["`cost_rate` is included only for CEO and CFO."])

ep(d="Company and Team", m="PATCH", p="/api/v1/members/{userId}", t="Update member role or details", auth="session",
   purpose="Change role, title, department, manager or cost rate.", perm="members.manage (cost_rate: finance.manage)", params="userId",
   idem="expected_version required.", audit="member.updated (fields)", event="member.role_changed", worker="Graph edge reports_to updated.",
   req={"expected_version": 1, "role": "manager", "department": "Engineering"},
   code=200, res=ok({"user_id": BILAL["user_id"], "role": "manager", "department": "Engineering", "version": 2}, "2026-10-12T06:00:00Z", "Member updated."),
   ecode=422, eres=err("ONE_CEO_ONLY", "A company has exactly one CEO. Transfer the CEO role from the CEO's own settings."),
   errs=[(200, "Updated"), (403, "AUTHORIZATION_DENIED"), (404, "NOT_FOUND"), (409, "VERSION_CONFLICT"), (422, "ONE_CEO_ONLY (DB-07)")], rules=["Role change takes effect on the next request."])

ep(d="Company and Team", m="POST", p="/api/v1/members/{userId}/deactivate", t="Deactivate member", auth="session",
   purpose="Remove access; open tasks and deals are reassigned; open work session is closed.", perm="members.manage", params="userId",
   idem="Idempotency-Key required.", audit="member.deactivated", event="member.deactivated", worker="Close live stream; revoke extension tokens.",
   req={"reassign_to": I("u-usman"), "reason": "Contract ended"},
   code=200, res=ok({"user_id": BILAL["user_id"], "status": "deactivated", "tasks_reassigned": 6, "deals_reassigned": 0, "work_session_closed": True}, "2026-10-12T12:00:00Z"),
   ecode=422, eres=err("CANNOT_DEACTIVATE_CEO", "The CEO cannot be deactivated."),
   errs=[(200, "Deactivated"), (403, "AUTHORIZATION_DENIED"), (404, "NOT_FOUND"), (422, "CANNOT_DEACTIVATE_CEO")], rules=["History stays; the person appears as 'Former member' in records."])

ep(d="Company and Team", m="GET", p="/api/v1/roles/permissions", t="Permissions matrix", auth="session",
   purpose="Screen 'Permissions Matrix' (read-only in Release 1; custom roles are Release 2).", perm="Any member", params="None",
   idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res=ok({"roles": ["ceo", "cto", "cfo", "coo", "hr", "manager", "employee"],
                     "matrix": {"room.view_live": ["ceo", "coo"], "hr.manage": ["ceo", "coo", "hr"], "leave.decide": ["ceo", "hr", "manager"],
                                "finance.manage": ["ceo", "cfo"], "crm.manage": ["ceo", "coo", "manager"], "rules.manage": ["ceo", "coo", "cto"]}}, "2026-10-12T04:05:00Z"),
   ecode=401, eres=err("AUTHENTICATION_REQUIRED", "Your session has expired. Sign in again."),
   errs=[(200, "Success"), (401, "AUTHENTICATION_REQUIRED")], rules=["The full matrix is in Section 7.2; this endpoint returns the same data."])

# ===================================================================== Employee Room
ep(d="Live Employee Room", m="POST", p="/api/v1/room/consent", t="Record monitoring consent", auth="session",
   purpose="Extension screen 'First-Install Consent': the employee reads the monitoring notice and accepts the current policy version.",
   perm="room.self (any member)", params="None", idem="Repeat for the same version returns the existing consent.",
   audit="room.consent_given / room.consent_revoked", event="room.consent_changed", worker="None.",
   req={"policy_version": 1, "accept": True},
   code=200, res=ok({"policy_version": 1, "consented_at": "2026-10-02T06:05:00Z", "covers": ["presence", "idle_state", "current_task", "live_screen_while_checked_in"],
                     "excludes": ["recording", "keystrokes", "browsing_history", "webcam", "microphone"]}, "2026-10-02T06:05:00Z", "Consent recorded."),
   ecode=409, eres=err("POLICY_VERSION_OUTDATED", "A newer monitoring notice exists. Read version 2 before accepting.", details={"current_version": 2}),
   errs=[(200, "Recorded"), (409, "POLICY_VERSION_OUTDATED")],
   rules=["Without current consent, check-in still works for attendance but the extension never starts screen sharing (OD-02 legal review).",
          "`accept: false` revokes consent and stops any active stream immediately."])

ep(d="Live Employee Room", m="POST", p="/api/v1/room/check-in", t="Check in", auth="session or extension",
   purpose="Extension 'Check-in' popup: opens the work session; returns an extension token and whether streaming is expected.",
   perm="room.self", params="None", idem="One open session per employee (DB-06); a repeat returns the open session.",
   audit="room.checked_in", event="room.checked_in", worker="Lateness rule (attendance.late).",
   req={"device": {"kind": "chrome_extension", "extension_version": "1.0.0"}, "task_id": I("task-auth-api")},
   code=201, res=ok({"session_id": I("ws-bilal-1012"), "started_at": T0, "minutes_late": 0, "presence": "active",
                     "extension_token": "ext_redacted_example", "heartbeat_seconds": 30, "streaming_required": True,
                     "next": "start_screen_share"}, T0, "Checked in at 9:02 AM."),
   extra=[("Repeat check-in while a session is open", 200, ok({"session_id": I("ws-bilal-1012"), "started_at": T0, "presence": "active", "already_open": True}, "2026-10-12T04:05:00Z"))],
   ecode=403, eres=err("ON_APPROVED_LEAVE", "You are on approved leave today. Ask HR to cancel the leave before checking in."),
   errs=[(201, "Session opened"), (200, "Already checked in"), (403, "ON_APPROVED_LEAVE"), (423, "MEMBER_DEACTIVATED")],
   rules=["Lateness = start minus (work start + grace) in the company time zone; 0 when on time.",
          "`streaming_required` is true only when the company enabled live view and the employee consented (API-017)."])

ep(d="Live Employee Room", m="POST", p="/api/v1/room/heartbeat", t="Presence heartbeat", auth="extension",
   purpose="Every 30 s from the extension: chrome.idle state, stream state, current task.", perm="Owner of the open session", params="None",
   idem="Heartbeats are idempotent by (session_id, sent_at).", audit="None (high volume).", event="room.presence_changed (only on change)", worker="Segments written on state change.",
   req={"session_id": I("ws-bilal-1012"), "sent_at": "2026-10-12T05:30:00Z", "idle_state": "active", "streaming": True, "task_id": I("task-auth-api")},
   code=200, res=ok({"presence": "active", "server_time": "2026-10-12T05:30:01Z", "next_heartbeat_seconds": 30, "pending_break_decision": None}, "2026-10-12T05:30:01Z"),
   ecode=409, eres=err("SESSION_CLOSED", "Your work session has ended. Check in again to continue."),
   errs=[(200, "Accepted"), (401, "Extension token invalid"), (409, "SESSION_CLOSED")],
   rules=["Server derives presence (engine/presence.py, PRS-01..02): no heartbeat for 90 s = offline.", "The extension sends no URLs, page titles, keystrokes or screenshots."])

ep(d="Live Employee Room", m="POST", p="/api/v1/room/check-out", t="Check out", auth="session or extension",
   purpose="Close the work session; stream stops; daily totals computed.", perm="room.self", params="None",
   idem="Repeat returns the closed session.", audit="room.checked_out", event="room.checked_out", worker="Daily summary for HR Agent; idle_paid_time detector input.",
   req={"session_id": I("ws-bilal-1012"), "note": "Auth API done, starting tests tomorrow"},
   code=200, res=ok({"session_id": I("ws-bilal-1012"), "started_at": T0, "ended_at": "2026-10-12T13:05:00Z",
                     "totals_minutes": {"active": 412, "idle": 38, "on_break": 45, "offline": 48}, "time_entries_created": 1}, "2026-10-12T13:05:00Z", "Checked out. Good work today."),
   ecode=409, eres=err("NO_OPEN_SESSION", "You are not checked in."),
   errs=[(200, "Closed"), (409, "NO_OPEN_SESSION")],
   rules=["Sessions still open 2 hours after work end are auto-closed at the last heartbeat (`auto_closed`).", "Active minutes on a task become a `room` time entry for that task."])

ep(d="Live Employee Room", m="POST", p="/api/v1/room/breaks", t="Request break", auth="session or extension",
   purpose="Extension 'Break Request Panel'.", perm="room.self", params="None",
   idem="One active break per employee (unique index).", audit="room.break_requested", event="room.break_requested", worker="Notify manager when approval is required.",
   req={"session_id": I("ws-bilal-1012"), "kind": "lunch", "minutes": 45},
   code=201, res=ok({"break_id": I("brk-1"), "status": "active", "started_at": "2026-10-12T08:00:00Z", "approval": "auto_approved_by_policy", "stream_paused": True}, "2026-10-12T08:00:00Z", "Lunch break started. Screen sharing paused."),
   ecode=409, eres=err("BREAK_ALREADY_ACTIVE", "You already have an active break."),
   errs=[(201, "Started or requested"), (409, "BREAK_ALREADY_ACTIVE / NO_OPEN_SESSION")],
   rules=["Policy (company setting): breaks up to the daily allowance start immediately; longer requests wait for a manager decision (API-022).", "Screen sharing pauses during breaks."])

ep(d="Live Employee Room", m="POST", p="/api/v1/room/breaks/{breakId}/decision", t="Approve or reject break", auth="session",
   purpose="Manager decides a break above the allowance.", perm="leave.decide for the employee's team", params="breakId",
   idem="First decision wins; later decisions return 409.", audit="room.break_decided", event="room.break_decided", worker="Notify employee.",
   req={"decision": "approved"},
   code=200, res=ok({"break_id": I("brk-2"), "status": "active", "started_at": "2026-10-12T10:00:00Z", "decided_by": I("u-usman")}, "2026-10-12T10:00:00Z"),
   ecode=409, eres=err("ALREADY_DECIDED", "This break request was already decided."),
   errs=[(200, "Decided"), (403, "AUTHORIZATION_DENIED"), (409, "ALREADY_DECIDED")], rules=["Rejected requests leave the employee in active presence."])

ep(d="Live Employee Room", m="POST", p="/api/v1/room/breaks/{breakId}/end", t="End break", auth="session or extension",
   purpose="Return from break; streaming resumes if consented.", perm="Break owner", params="breakId",
   idem="Repeat returns the ended break.", audit="room.break_ended", event="room.break_ended", worker="None.", req={},
   code=200, res=ok({"break_id": I("brk-1"), "status": "ended", "minutes": 45, "over_allowance_minutes": 0, "stream_resume": True}, "2026-10-12T08:45:00Z"),
   ecode=404, eres=err("NOT_FOUND", "Break not found."),
   errs=[(200, "Ended"), (404, "NOT_FOUND")], rules=["Over-allowance minutes are reported to HR, not deducted automatically."])

ep(d="Live Employee Room", m="POST", p="/api/v1/room/stream/publish-token", t="Get screen-share publish token", auth="extension",
   purpose="The extension offscreen document gets a LiveKit token to publish the employee's screen to the company room.",
   perm="Checked in, consented, not on break", params="None", idem="New short-lived token each call.",
   audit="room.stream_started", event="room.stream_state", worker="None.",
   req={"session_id": I("ws-bilal-1012")},
   code=200, res=ok({"livekit_url": "wss://media.ems.example", "token": "eyJ...redacted", "room": "ems-" + I("org-acme") + "-" + BILAL["user_id"], "identity": "employee:" + BILAL["user_id"],
                     "grants": {"can_publish": True, "can_subscribe": False, "can_publish_data": False, "can_publish_sources": ["screen_share"]}, "expires_in_seconds": 600,
                     "video": {"max_resolution": "1280x720", "max_fps": 5}}, "2026-10-12T04:02:30Z"),
   ecode=403, eres=err("CONSENT_REQUIRED", "Accept the monitoring notice before sharing your screen.", details={"policy_version": 1}),
   errs=[(200, "Token issued"), (403, "CONSENT_REQUIRED / ON_BREAK"), (409, "NO_OPEN_SESSION"), (503, "MEDIA_UNAVAILABLE")],
   rules=["Token built with livekit-api 1.2.1 `AccessToken(key, secret).with_identity(...).with_ttl(timedelta(seconds=600)).with_grants(VideoGrants(room_join=True, room=..., can_publish=True, can_subscribe=False, can_publish_data=False, can_publish_sources=['screen_share']))`; one LiveKit room per employee (locally checked, tools/check_livekit_tokens.py LK-01..03, EV-004).",
          "Chrome requires the employee to pick the screen in the picker each time sharing starts; it cannot be started silently (EV-001)."])

ep(d="Live Employee Room", m="GET", p="/api/v1/room/live", t="CEO live grid", auth="session",
   purpose="'CEO Live Grid': everyone checked in, presence, current task, stream availability.", perm="room.view_live (CEO, COO)", params="department, presence, cursor, limit (max 48)",
   idem="Read-only; refresh every 15 s or via server-sent events.", audit="None (viewing a stream is audited by API-026).", event="None.", worker="None.",
   code=200, res=ok({"as_of": "2026-10-12T05:30:05Z", "counts": {"checked_in": 12, "active": 9, "idle": 1, "on_break": 2, "offline": 0, "not_checked_in": 2, "on_leave": 1},
                     "items": [{"user_id": BILAL["user_id"], "name": "Bilal Ahmed", "department": "Engineering", "presence": "active", "since": T0,
                                "current_task": {"id": I("task-auth-api"), "title": "Auth API"}, "stream": "live", "minutes_late": 0},
                               {"user_id": I("u-ayesha"), "name": "Ayesha Noor", "department": "Design", "presence": "on_break", "since": "2026-10-12T05:20:00Z",
                                "current_task": None, "stream": "paused", "minutes_late": 12}],
                     "next_cursor": None}, "2026-10-12T05:30:05Z"),
   ecode=403, eres=err("AUTHORIZATION_DENIED", "Only the CEO and COO can open the live room."),
   errs=[(200, "Success"), (403, "AUTHORIZATION_DENIED")], rules=["Thumbnails are not stored; the grid shows the live track only when a viewer opens it (API-026)."])

ep(d="Live Employee Room", m="POST", p="/api/v1/room/stream/view", t="Open a live screen view", auth="session",
   purpose="'Full-Screen Monitoring': subscribe to one employee's screen; the view is logged and visible to that employee.",
   perm="room.view_live", params="None", idem="Each call opens a new view record.", audit="room.stream_viewed (viewer, subject, reason)", event="room.view_started (employee is notified in the extension)", worker="None.",
   req={"subject_user_id": BILAL["user_id"], "reason": "Daily stand-up check"},
   code=201, res=ok({"view_id": I("view-1"), "livekit_url": "wss://media.ems.example", "token": "eyJ...redacted",
                     "room": "ems-" + I("org-acme") + "-" + BILAL["user_id"], "grants": {"can_publish": False, "can_subscribe": True, "can_publish_data": False}, "expires_in_seconds": 900, "subject_notified": True}, "2026-10-12T05:31:00Z"),
   ecode=409, eres=err("STREAM_NOT_LIVE", "Bilal is not sharing right now (on break or not checked in).", details={"presence": "on_break"}),
   errs=[(201, "View opened"), (400, "VALIDATION_FAILED - reason required"), (403, "AUTHORIZATION_DENIED"), (409, "STREAM_NOT_LIVE")],
   rules=["A reason of 3-200 characters is required (stream_views CHECK).", "Release 1 never records video; recording history is Release 2 and needs OD-02."])

ep(d="Live Employee Room", m="POST", p="/api/v1/room/stream/view/{viewId}/end", t="Close a live view", auth="session",
   purpose="End the view record when the viewer closes the stream.", perm="The viewer", params="viewId",
   idem="Repeat returns the closed view.", audit="room.stream_view_ended", event="None.", worker="Views open longer than the token lifetime are closed by the sweeper.", req={},
   code=200, res=ok({"view_id": I("view-1"), "started_at": "2026-10-12T05:31:00Z", "ended_at": "2026-10-12T05:34:20Z", "seconds": 200}, "2026-10-12T05:34:20Z"),
   ecode=404, eres=err("NOT_FOUND", "View not found."),
   errs=[(200, "Closed"), (404, "NOT_FOUND")], rules=["Only `ended_at` can change on a view record (DB-13)."])

ep(d="Live Employee Room", m="GET", p="/api/v1/room/my-viewers", t="Who viewed my screen", auth="session or extension",
   purpose="Transparency: an employee sees every view of their screen with viewer, time and reason.", perm="room.self", params="from, to",
   idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res=ok({"items": [{"view_id": I("view-1"), "viewer": "Imran Qureshi", "reason": "Daily stand-up check", "started_at": "2026-10-12T05:31:00Z", "seconds": 200}]}, "2026-10-12T06:00:00Z"),
   ecode=401, eres=err("AUTHENTICATION_REQUIRED", "Your session has expired. Sign in again."),
   errs=[(200, "Success"), (401, "AUTHENTICATION_REQUIRED")], rules=["Cannot be disabled by any role."])

# ===================================================================== HRM
ep(d="People and HR", m="GET", p="/api/v1/employees", t="Employee directory", auth="session",
   purpose="'Employee Directory' with today's attendance state.", perm="hr.manage, or manager for own team", params="department, status, q, cursor, limit",
   idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res=ok({"items": [{"user_id": BILAL["user_id"], "name": "Bilal Ahmed", "title": "Backend Developer", "department": "Engineering", "manager": "Usman Tariq",
                                "today": {"state": "checked_in", "since": T0, "minutes_late": 0}, "leave_balance_days": {"annual": 14, "casual": 6}}], "next_cursor": None}, "2026-10-12T05:00:00Z"),
   ecode=403, eres=err("AUTHORIZATION_DENIED", "You can only see your own profile."),
   errs=[(200, "Success"), (403, "AUTHORIZATION_DENIED")], rules=["Leave balances are computed from policy and approved leave (Section 10)."])

ep(d="People and HR", m="GET", p="/api/v1/attendance", t="Attendance and timesheets", auth="session",
   purpose="'Attendance and Timesheets': per-day totals from work sessions and presence segments.", perm="hr.manage; employees see their own", params="user_id, from, to (dates, company time zone)",
   idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res=ok({"user_id": BILAL["user_id"], "days": [{"date": "2026-10-12", "check_in": "09:02", "check_out": "18:05", "minutes_late": 0,
                                                           "active": 412, "idle": 38, "on_break": 45, "offline": 48, "status": "present"},
                                                          {"date": "2026-10-13", "status": "not_checked_in"}],
                     "totals": {"present_days": 1, "late_days": 0, "active_minutes": 412}}, "2026-10-13T06:00:00Z"),
   ecode=400, eres=err("VALIDATION_FAILED", "Choose a range of at most 62 days."),
   errs=[(200, "Success"), (400, "VALIDATION_FAILED"), (403, "AUTHORIZATION_DENIED")], rules=["Times are shown in the company time zone; storage is UTC."])

ep(d="People and HR", m="POST", p="/api/v1/leave-requests", t="Request leave", auth="session",
   purpose="'Leave Request'.", perm="Any member for self", params="None",
   idem="Idempotency-Key required; overlapping requests are rejected by the database (DB-08).", audit="leave.requested", event="leave.requested", worker="leave.requested rules; notify approver.",
   req={"kind": "annual", "start_date": "2026-10-20", "end_date": "2026-10-22", "reason": "Family event"},
   code=201, res=ok({"request_id": I("lr-bilal"), "status": "pending", "days": 3, "approver": "Imran Qureshi", "balance_after_approval": {"annual": 11}}, "2026-10-12T06:00:00Z", "Leave request sent to Imran Qureshi."),
   ecode=409, eres=err("LEAVE_OVERLAP", "You already have leave requested or approved for part of these dates."),
   errs=[(201, "Requested"), (400, "VALIDATION_FAILED"), (409, "LEAVE_OVERLAP"), (422, "INSUFFICIENT_BALANCE")],
   rules=["Days count working days only (company calendar).", "Approver: manager if set, else HR; CEO approves for leadership roles and when the company enables 'CEO Leave Approval'."])

ep(d="People and HR", m="GET", p="/api/v1/leave-requests", t="List leave requests", auth="session",
   purpose="Approver queue and the employee's own history.", perm="Own requests; approvers see their queue", params="status, scope (mine|to_decide), cursor",
   idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res=ok({"items": [{"request_id": I("lr-bilal"), "employee": "Bilal Ahmed", "kind": "annual", "start_date": "2026-10-20", "end_date": "2026-10-22", "days": 3, "status": "pending",
                                "team_on_leave_same_days": 1}], "next_cursor": None}, "2026-10-12T07:00:00Z"),
   ecode=401, eres=err("AUTHENTICATION_REQUIRED", "Your session has expired. Sign in again."),
   errs=[(200, "Success"), (401, "AUTHENTICATION_REQUIRED")], rules=["`team_on_leave_same_days` helps approvers avoid staffing gaps."])

ep(d="People and HR", m="POST", p="/api/v1/leave-requests/{requestId}/decision", t="Approve or reject leave", auth="session",
   purpose="'CEO Leave Approval' and manager/HR approval.", perm="leave.decide for this employee", params="requestId",
   idem="expected_version required; first decision wins.", audit="leave.decided", event="leave.decided", worker="Notify employee; graph and attendance calendars updated.",
   req={"expected_version": 1, "decision": "approved", "note": "Enjoy"},
   code=200, res=ok({"request_id": I("lr-bilal"), "status": "approved", "decided_by": "Imran Qureshi", "decided_at": "2026-10-12T07:05:00Z", "version": 2}, "2026-10-12T07:05:00Z"),
   ecode=409, eres=err("VERSION_CONFLICT", "This request was already decided.", details={"current_status": "approved"}),
   errs=[(200, "Decided"), (403, "AUTHORIZATION_DENIED - cannot approve own leave"), (409, "VERSION_CONFLICT")], rules=["Nobody can approve their own leave."])

ep(d="People and HR", m="GET", p="/api/v1/hr/reports/daily", t="Daily and weekly HR report", auth="session",
   purpose="'Daily/Weekly Reports': attendance, lateness, leave, idle above threshold, top tasks.", perm="hr.manage", params="date or week (ISO week, e.g. 2026-W42)",
   idem="Read-only; built from closed sessions.", audit="None.", event="None.", worker="Nightly pre-computation at 23:30 company time.",
   code=200, res=ok({"date": "2026-10-12", "headcount": 15, "present": 12, "on_leave": 1, "absent_unexplained": 2, "late": [{"name": "Ayesha Noor", "minutes": 12}],
                     "idle_over_threshold": [{"name": "Ayesha Noor", "idle_minutes": 74}], "break_over_allowance": [],
                     "active_minutes_total": 4380, "notes": "Idle time is a review signal, not a performance score."}, "2026-10-12T19:00:00Z"),
   ecode=403, eres=err("AUTHORIZATION_DENIED", "Only HR and leadership can view company reports."),
   errs=[(200, "Success"), (403, "AUTHORIZATION_DENIED")], rules=["Absent = no session, no approved leave, working day."])

ep(d="People and HR", m="POST", p="/api/v1/hr-agent/ask", t="Ask the HR Agent", auth="session",
   purpose="'HR Agent Query and Work Summary': rule-based answers from EMS records with sources; no language model.", perm="Any member (scope limited by role)", params="None",
   idem="Read-only.", audit="agent_logs (intent only; the question text is not stored)", event="None.", worker="None.",
   req={"question": "Who is on leave today?"},
   code=200, res=ok({"intent": "who_on_leave", "answered": True, "text": "1 on leave on 2026-10-12: Hina Shah (annual)",
                     "data": [{"user_id": I("u-hina"), "name": "Hina Shah", "kind": "annual", "request_id": I("lr-hina")}], "sources": [I("lr-hina")]}, "2026-10-12T06:00:00Z"),
   extra=[("Question outside the agent's knowledge (never guessed)", 200, ok({"intent": "unknown", "answered": False,
            "text": "I can't answer that from EMS records. I can answer: Who is on leave today?; Which leave requests are pending?; Who came late today?; Who is online now?; Work summary for <name> yesterday; What is the leave policy?",
            "data": [], "sources": []}, "2026-10-12T06:00:00Z"))],
   ecode=400, eres=err("VALIDATION_FAILED", "Ask a question of 3 to 300 characters."),
   errs=[(200, "Answered or explained why not"), (400, "VALIDATION_FAILED")], rules=["Implemented by engine/hr_agent.py (AGT-01..05). Employees cannot query other people's data."])

ep(d="People and HR", m="GET", p="/api/v1/hr-agent/policies", t="List HR policies", auth="session",
   purpose="'HR Agent Rules and Policies': published policies the agent quotes.", perm="Any member", params="None",
   idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res=ok({"items": [{"topic": "leave", "version": 2, "text": "18 annual days and 8 casual days per year. Requests 3+ days need 7 days' notice.", "published_at": "2026-10-01T06:00:00Z"},
                               {"topic": "attendance", "version": 1, "text": "Work hours 09:00-18:00, 10 minutes grace. Lunch 45 minutes.", "published_at": "2026-10-01T06:00:00Z"}]}, "2026-10-12T06:00:00Z"),
   ecode=401, eres=err("AUTHENTICATION_REQUIRED", "Your session has expired. Sign in again."),
   errs=[(200, "Success"), (401, "AUTHENTICATION_REQUIRED")], rules=["Policies are plain text written by HR; the agent quotes them verbatim with the version."])

ep(d="People and HR", m="PUT", p="/api/v1/hr-agent/policies/{topic}", t="Publish HR policy", auth="session",
   purpose="HR publishes a new version of a policy and its machine rules (allowances, grace).", perm="hr.manage", params="topic (leave|attendance|breaks|general|monitoring)",
   idem="expected_version required; creates version n+1.", audit="policy.published", event="policy.published", worker="Rules referencing the policy reload.",
   req={"expected_version": 1, "text": "Work hours 09:00-18:00, 15 minutes grace. Lunch 45 minutes.", "rules": {"late_grace_minutes": 15, "daily_break_allowance_minutes": 60}},
   code=200, res=ok({"topic": "attendance", "version": 2, "published_at": "2026-10-12T07:00:00Z"}, "2026-10-12T07:00:00Z", "Attendance policy v2 published."),
   ecode=409, eres=err("VERSION_CONFLICT", "Someone published a newer version. Reload first.", details={"current_version": 2}),
   errs=[(200, "Published"), (403, "AUTHORIZATION_DENIED"), (409, "VERSION_CONFLICT")], rules=["Changing the monitoring notice (room policy) also bumps the consent version (API-017)."])

# ===================================================================== Projects
PROJ = I("proj-northwind")
ep(d="Projects and Tasks", m="GET", p="/api/v1/projects", t="Projects dashboard and list", auth="session",
   purpose="'Projects Dashboard and List' with progress, budget burn and overdue counts.", perm="Members see projects they are on; projects.manage sees all", params="status, client_id, cursor, limit",
   idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res=ok({"items": [{"id": PROJ, "name": "Northwind website", "client": "Northwind Digital", "status": "active", "billing_type": "fixed",
                                "progress_pct": 40, "tasks": {"todo": 6, "active": 3, "review": 1, "done": 7}, "overdue": 1,
                                "budget": {"amount": "5000.00", "cost_to_date": "1820.00", "currency": "USD", "ratio": "0.36"}}], "next_cursor": None}, "2026-10-12T06:00:00Z"),
   ecode=401, eres=err("AUTHENTICATION_REQUIRED", "Your session has expired. Sign in again."),
   errs=[(200, "Success"), (401, "AUTHENTICATION_REQUIRED")], rules=["Budget figures appear only for finance.manage and project owners; cost uses member cost rates."])

ep(d="Projects and Tasks", m="POST", p="/api/v1/projects", t="Create project", auth="session",
   purpose="Create a client or internal project.", perm="projects.manage", params="None",
   idem="Idempotency-Key required.", audit="project.created", event="project.created", worker="Graph node + edges (client, owner).",
   req={"name": "Contoso support", "client_id": I("client-contoso"), "billing_type": "hourly", "hourly_rate": "40.00", "currency": "USD", "owner_id": I("u-usman")},
   code=201, res=ok({"id": I("proj-contoso"), "name": "Contoso support", "status": "planned", "billing_type": "hourly", "version": 1}, "2026-10-12T06:10:00Z", "Project created."),
   ecode=400, eres=err("VALIDATION_FAILED", "Hourly projects need an hourly rate and currency.", details={"fields": {"hourly_rate": "Required for hourly billing."}}),
   errs=[(201, "Created"), (400, "VALIDATION_FAILED (DB-10 constraints)"), (403, "AUTHORIZATION_DENIED")], rules=["Non-internal projects require a client."])

ep(d="Projects and Tasks", m="GET", p="/api/v1/projects/{projectId}/board", t="Project details and Kanban", auth="session",
   purpose="'Project Details and Kanban': columns To do, Active, Review, Done.", perm="Project member or projects.manage", params="projectId, assignee_id",
   idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res=ok({"project": {"id": PROJ, "name": "Northwind website", "client": "Northwind Digital"},
                     "columns": {"todo": [{"id": I("task-seo"), "title": "SEO audit", "assignee": "Ayesha Noor", "due_at": "2026-10-16T13:00:00Z", "position": 1, "version": 1}],
                                 "active": [{"id": I("task-auth-api"), "title": "Auth API", "assignee": "Bilal Ahmed", "due_at": "2026-10-12T13:00:00Z", "position": 1, "version": 3, "minutes_logged": 300}],
                                 "review": [], "done": []}}, "2026-10-12T06:00:00Z"),
   ecode=404, eres=err("NOT_FOUND", "Project not found."),
   errs=[(200, "Success"), (404, "NOT_FOUND")], rules=["Each column is capped at 200 cards; older done cards are paginated."])

ep(d="Projects and Tasks", m="POST", p="/api/v1/projects/{projectId}/tasks", t="Create task", auth="session",
   purpose="'Create/Edit Task'.", perm="Project member", params="projectId", idem="Idempotency-Key required.", audit="task.created", event="task.created", worker="Graph edge works_on for the assignee.",
   req={"title": "Payment page", "assignee_id": BILAL["user_id"], "due_at": "2026-10-15T13:00:00Z", "estimate_minutes": 480, "billable": True},
   code=201, res=ok({"id": I("task-payment"), "status": "todo", "position": 2, "version": 1}, "2026-10-12T06:20:00Z", "Task created."),
   ecode=422, eres=err("ASSIGNEE_NOT_MEMBER", "The assignee is not an active member of this company."),
   errs=[(201, "Created"), (400, "VALIDATION_FAILED"), (422, "ASSIGNEE_NOT_MEMBER")], rules=["Due times are stored in UTC and shown in the company time zone."])

ep(d="Projects and Tasks", m="PATCH", p="/api/v1/tasks/{taskId}", t="Edit task", auth="session",
   purpose="Edit title, assignee, due date, estimate, billable.", perm="Project member", params="taskId",
   idem="expected_version required.", audit="task.updated", event="task.updated", worker="None.",
   req={"expected_version": 3, "due_at": "2026-10-13T13:00:00Z"},
   code=200, res=ok({"id": I("task-auth-api"), "due_at": "2026-10-13T13:00:00Z", "version": 4}, "2026-10-12T07:00:00Z"),
   ecode=409, eres=err("VERSION_CONFLICT", "This task was changed by someone else.", details={"current_version": 4}),
   errs=[(200, "Updated"), (409, "VERSION_CONFLICT")], rules=["Status changes use API-043."])

ep(d="Projects and Tasks", m="POST", p="/api/v1/tasks/{taskId}/move", t="Move task on the board", auth="session",
   purpose="Drag between Kanban columns or reorder.", perm="Project member", params="taskId",
   idem="expected_version required.", audit="task.moved", event="task.status_changed", worker="Rules on task.status (e.g. review -> notify owner).",
   req={"expected_version": 4, "to_status": "review", "position": 1},
   code=200, res=ok({"id": I("task-auth-api"), "status": "review", "position": 1, "version": 5}, "2026-10-12T12:30:00Z"),
   ecode=422, eres=err("INVALID_TRANSITION", "Tasks move to Done only from Review.", details={"from": "active", "to": "done", "allowed": ["todo", "review"]}),
   errs=[(200, "Moved"), (409, "VERSION_CONFLICT"), (422, "INVALID_TRANSITION")], rules=["Allowed: todo<->active, active<->review, review->done, done->review (reopen)."])

ep(d="Projects and Tasks", m="POST", p="/api/v1/tasks/{taskId}/time-entries", t="Log time manually", auth="session",
   purpose="Add time not captured by the Room (meetings, offline work).", perm="Assignee or project manager", params="taskId",
   idem="Idempotency-Key required.", audit="time.logged", event="time.logged", worker="unbilled_time detector input.",
   req={"started_at": "2026-10-12T10:00:00Z", "minutes": 60, "billable": True, "note": "Client call"},
   code=201, res=ok({"time_entry_id": I("te-1"), "source": "manual", "minutes": 60, "billable": True}, "2026-10-12T11:05:00Z"),
   ecode=409, eres=err("TIME_OVERLAPS_SESSION", "This time overlaps your Room session, which already counted it.", details={"session_id": I("ws-bilal-1012")}),
   errs=[(201, "Logged"), (400, "VALIDATION_FAILED"), (409, "TIME_OVERLAPS_SESSION")], rules=["Manual entries cannot overlap a Room session of the same person (prevents double billing)."])

# ===================================================================== CRM and client lifecycle
CONTACT, DEAL, CLIENT = I("contact-ali"), I("deal-northwind"), I("client-northwind")
ep(d="CRM and Client Lifecycle", m="POST", p="/api/v1/contacts", t="Create contact or lead", auth="session",
   purpose="'Contacts and Leads List': add a person and optional company.", perm="crm.manage", params="None",
   idem="Idempotency-Key required; same email returns the existing contact (unique per company).", audit="contact.created", event="contact.created", worker="Graph nodes (contact, company).",
   req={"name": "Ali Raza", "email": "ali@northwind.example", "phone": "+923001234567", "company": {"name": "Northwind Digital", "domain": "northwind.example"}, "source": "referral"},
   code=201, res=ok({"id": CONTACT, "lifecycle_stage": "lead", "company_id": I("company-northwind"), "owner": "Usman Tariq", "version": 1}, "2026-09-20T06:00:00Z", "Lead added."),
   extra=[("Duplicate email", 200, ok({"id": CONTACT, "lifecycle_stage": "lead", "already_exists": True}, "2026-09-21T06:00:00Z"))],
   ecode=422, eres=err("SUPPRESSED_CONTACT", "This email asked not to be contacted. It cannot be added as a lead."),
   errs=[(201, "Created"), (200, "Already exists"), (400, "VALIDATION_FAILED"), (422, "SUPPRESSED_CONTACT")], rules=["Suppression list is checked by hashed email/domain (API-060)."])

ep(d="CRM and Client Lifecycle", m="POST", p="/api/v1/contacts/search", t="Search contacts", auth="session",
   purpose="Filter by stage, owner, source and text; text in the body, not the URL.", perm="crm.manage or cfo (read)", params="None (body)",
   idem="Read-only POST.", audit="None.", event="None.", worker="None.",
   req={"query": "northwind", "lifecycle_stage": ["lead", "qualified", "opportunity"], "limit": 25, "cursor": None},
   code=200, res=ok({"items": [{"id": CONTACT, "name": "Ali Raza", "company": "Northwind Digital", "lifecycle_stage": "opportunity", "owner": "Usman Tariq", "last_activity_at": "2026-09-28T07:00:00Z"}], "next_cursor": None}, "2026-10-12T06:00:00Z"),
   ecode=400, eres=err("VALIDATION_FAILED", "Search text must be at least 2 characters."),
   errs=[(200, "Success"), (400, "VALIDATION_FAILED")], rules=["Uses pg_trgm indexes on name/email/company (TASK-010)."])

ep(d="CRM and Client Lifecycle", m="GET", p="/api/v1/contacts/{contactId}", t="Contact and lead details", auth="session",
   purpose="'Contact/Lead Details' with deals, activities and related people from graph memory.", perm="crm.manage or cfo", params="contactId",
   idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res=ok({"id": CONTACT, "name": "Ali Raza", "email": "ali@northwind.example", "company": {"id": I("company-northwind"), "name": "Northwind Digital"},
                     "lifecycle_stage": "customer", "deals": [{"id": DEAL, "title": "Website rebuild", "stage": "won", "amount": "5000.00", "currency": "USD"}],
                     "activities": [{"kind": "meeting", "note": "Scope workshop", "occurred_at": "2026-09-28T07:00:00Z", "actor": "Usman Tariq"}],
                     "related": [{"kind": "project", "label": "Northwind website", "via": ["contact_of", "originated_from", "billed_by"]}]}, "2026-10-12T06:00:00Z"),
   ecode=404, eres=err("NOT_FOUND", "Contact not found."),
   errs=[(200, "Success"), (404, "NOT_FOUND")], rules=["`related` comes from ems.graph_neighbors (DB-11), depth 3 max."])

ep(d="CRM and Client Lifecycle", m="POST", p="/api/v1/deals", t="Create deal", auth="session",
   purpose="Add an opportunity to the pipeline.", perm="crm.manage", params="None",
   idem="Idempotency-Key required.", audit="deal.created", event="deal.created", worker="Graph edges; contact stage -> opportunity.",
   req={"contact_id": CONTACT, "title": "Website rebuild", "amount": "5000.00", "currency": "USD", "expected_close": "2026-10-10", "owner_id": I("u-usman")},
   code=201, res=ok({"id": DEAL, "stage": "new", "version": 1}, "2026-09-20T06:10:00Z", "Deal created."),
   ecode=400, eres=err("VALIDATION_FAILED", "Amount must be zero or more.", details={"fields": {"amount": ">= 0"}}),
   errs=[(201, "Created"), (400, "VALIDATION_FAILED"), (403, "AUTHORIZATION_DENIED")], rules=["Currency is ISO 4217; amounts are decimal strings."])

ep(d="CRM and Client Lifecycle", m="GET", p="/api/v1/deals/pipeline", t="Sales pipeline board", auth="session",
   purpose="'Sales Pipeline Board' and 'CRM Dashboard' totals.", perm="crm.manage or cfo", params="owner_id, currency (required if several)",
   idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res=ok({"currency": "USD", "stages": [{"stage": "new", "count": 4, "amount": "12000.00"}, {"stage": "qualified", "count": 3, "amount": "9500.00"},
                                                  {"stage": "proposal", "count": 2, "amount": "8000.00"}, {"stage": "negotiation", "count": 1, "amount": "6000.00"}],
                     "weighted_open": "11775.00", "won_this_month": {"count": 1, "amount": "5000.00"}, "stale_count": 2}, "2026-10-12T06:00:00Z"),
   ecode=400, eres=err("CURRENCY_REQUIRED", "Choose a currency; deals exist in USD and PKR."),
   errs=[(200, "Success"), (400, "CURRENCY_REQUIRED")], rules=["Weighted = sum(amount x stage probability) using engine/leakage.py STAGE_PROBABILITY."])

ep(d="CRM and Client Lifecycle", m="POST", p="/api/v1/deals/{dealId}/stage", t="Move deal stage", auth="session",
   purpose="Advance or lose a deal.", perm="crm.manage", params="dealId",
   idem="expected_version required.", audit="deal.stage_changed", event="deal.stage_changed", worker="Rules; stale timer resets.",
   req={"expected_version": 3, "to_stage": "negotiation"},
   code=200, res=ok({"id": DEAL, "stage": "negotiation", "version": 4}, "2026-10-02T06:00:00Z"),
   ecode=422, eres=err("INVALID_TRANSITION", "Use 'Mark as won' to win a deal.", details={"to": "won", "use": "/api/v1/deals/{dealId}/win"}),
   errs=[(200, "Moved"), (409, "VERSION_CONFLICT"), (422, "INVALID_TRANSITION / LOST_REASON_REQUIRED")], rules=["`lost` requires `lost_reason` (DB-09)."])

ep(d="CRM and Client Lifecycle", m="POST", p="/api/v1/deals/{dealId}/win", t="Win deal and start client lifecycle", auth="session",
   purpose="One transaction: deal won, client created, kickoff project created from a template, contact becomes customer.", perm="crm.manage", params="dealId",
   idem="Idempotency-Key required; one client per deal (DB-09) so retries return the same client.", audit="deal.won, client.created, project.created", event="deal.won", worker="Graph edges; won_follow_through detector clears.",
   req={"expected_version": 4, "project": {"name": "Northwind website", "billing_type": "fixed", "budget_amount": "5000.00", "owner_id": I("u-usman"), "template": "website_standard"}, "renewal_date": "2027-10-10"},
   code=200, res=ok({"deal": {"id": DEAL, "stage": "won", "won_at": "2026-10-03T06:00:00Z"}, "client": {"id": CLIENT, "status": "onboarding"},
                     "project": {"id": PROJ, "status": "planned", "tasks_created": 12}}, "2026-10-03T06:00:00Z", "Deal won. Client and project created."),
   ecode=409, eres=err("ALREADY_WON", "This deal is already won.", details={"client_id": CLIENT}),
   errs=[(200, "Won (or replayed)"), (409, "ALREADY_WON / VERSION_CONFLICT"), (422, "COMPANY_REQUIRED")], rules=["Without a project the won deal shows a leakage finding after 3 days (LEK-04)."])

ep(d="CRM and Client Lifecycle", m="POST", p="/api/v1/activities", t="Log activity", auth="session",
   purpose="Call, email, meeting or note on a contact, deal, client or project.", perm="crm.manage or project member", params="None",
   idem="Idempotency-Key required.", audit="activity.created", event="activity.created", worker="Updates deal.last_activity_at (stale timer).",
   req={"entity_type": "deal", "entity_id": DEAL, "kind": "call", "note": "Agreed payment terms", "occurred_at": "2026-10-02T05:30:00Z"},
   code=201, res=ok({"id": I("act-1"), "entity_type": "deal", "entity_id": DEAL}, "2026-10-02T05:31:00Z"),
   ecode=400, eres=err("VALIDATION_FAILED", "Activity time cannot be in the future."),
   errs=[(201, "Logged"), (400, "VALIDATION_FAILED"), (404, "NOT_FOUND")], rules=["Activities are append-only."])

ep(d="CRM and Client Lifecycle", m="POST", p="/api/v1/invoices", t="Record invoice", auth="session",
   purpose="Record an invoice issued to a client (EMS does not send or collect payment in Release 1).", perm="finance.manage", params="None",
   idem="Idempotency-Key required; number unique per company.", audit="invoice.recorded", event="invoice.recorded", worker="Marks included time entries invoiced; leakage detectors.",
   req={"client_id": CLIENT, "project_id": PROJ, "number": "INV-2026-1048", "amount": "2500.00", "currency": "USD", "issued_on": "2026-10-05", "due_on": "2026-10-19", "time_entry_ids": []},
   code=201, res=ok({"id": I("inv-1048"), "status": "sent", "outstanding": "2500.00"}, "2026-10-05T06:00:00Z", "Invoice INV-2026-1048 recorded."),
   ecode=409, eres=err("INVOICE_NUMBER_TAKEN", "Invoice number INV-2026-1048 already exists."),
   errs=[(201, "Recorded"), (400, "VALIDATION_FAILED - due before issue"), (409, "INVOICE_NUMBER_TAKEN")], rules=["Billing integration (sending invoices, online payment) is Release 2 (report: 'Billing (future)')."])

ep(d="CRM and Client Lifecycle", m="POST", p="/api/v1/invoices/{invoiceId}/payments", t="Record payment", auth="session",
   purpose="Record money received; status becomes partially_paid or paid.", perm="finance.manage", params="invoiceId",
   idem="Idempotency-Key required; payments are append-only.", audit="payment.recorded", event="payment.recorded", worker="overdue_invoice findings resolve automatically.",
   req={"amount": "2500.00", "received_on": "2026-10-18", "method": "bank_transfer"},
   code=201, res=ok({"payment_id": I("pay-1"), "invoice_status": "paid", "outstanding": "0.00"}, "2026-10-18T06:00:00Z"),
   ecode=422, eres=err("OVERPAYMENT", "Payment exceeds the outstanding amount of 2500.00 USD."),
   errs=[(201, "Recorded"), (422, "OVERPAYMENT")], rules=["Corrections are negative adjustments in Release 2; Release 1 voids and re-records."])

# ===================================================================== Lead Hunter
HUNT = I("hunt-1")
ep(d="Lead Hunter", m="POST", p="/api/v1/hunts", t="Start a hunt", auth="session",
   purpose="'Search and Filters': crawl user-supplied company websites and score them against an ideal-customer profile.", perm="hunter.use", params="None",
   idem="Idempotency-Key required.", audit="hunt.created", event="hunt.created", worker="Crawler job (robots.txt per RFC 9309, 1 request / 5 s per domain).",
   req={"name": "Lahore marketing agencies", "seeds": {"domains": ["brightpixel.example", "adsmiths.example", "northwind.example"]},
        "icp": {"industry_keywords": ["marketing agency", "digital agency"], "countries": ["PK"], "tech": ["wordpress", "shopify"], "min_team_size": 10}, "max_pages_per_domain": 5},
   code=202, res=ok({"hunt_id": HUNT, "status": "queued", "domains": 3, "estimated_minutes": 2}, "2026-10-12T06:00:00Z", "Hunt started."),
   ecode=422, eres=err("SOURCE_NOT_ALLOWED", "linkedin.com cannot be crawled. Use company websites you are allowed to visit.", details={"domain": "linkedin.com"}),
   errs=[(202, "Queued"), (400, "VALIDATION_FAILED - max 200 domains"), (422, "SOURCE_NOT_ALLOWED")],
   rules=["Release 1 seeds are domains the user supplies or imports; EMS does not scrape search engines or social networks (blocklist: linkedin.com, facebook.com, instagram.com, x.com, google.* search).",
          "Only pages allowed by robots.txt are fetched; 5xx/unreachable robots.txt means do not crawl (ROB-03)."])

ep(d="Lead Hunter", m="GET", p="/api/v1/hunts/{huntId}", t="Hunt status", auth="session",
   purpose="'Lead Hunter Dashboard': progress and crawl outcomes.", perm="hunter.use", params="huntId",
   idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res=ok({"hunt_id": HUNT, "status": "completed", "stats": {"domains": 3, "fetched_pages": 11, "robots_disallowed": 2, "unreachable": 0, "prospects": 2, "already_in_crm": 1}}, "2026-10-12T06:03:00Z"),
   ecode=404, eres=err("NOT_FOUND", "Hunt not found."),
   errs=[(200, "Success"), (404, "NOT_FOUND")], rules=["`already_in_crm` domains are skipped, not duplicated."])

ep(d="Lead Hunter", m="GET", p="/api/v1/hunts/{huntId}/prospects", t="Results and scoring", auth="session",
   purpose="'Results and Scoring' with reasons for every point.", perm="hunter.use", params="huntId, min_score, cursor",
   idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res=ok({"items": [{"id": I("pr-bright"), "domain": "brightpixel.example", "company_name": "BrightPixel", "score": 85,
                                "score_reasons": ["industry keywords: marketing agency", "country PK", "contact page found", "public business email listed", "uses wordpress"],
                                "public_emails": ["info@brightpixel.example"], "source_url": "https://brightpixel.example/about", "status": "new"}], "next_cursor": None}, "2026-10-12T06:03:30Z"),
   ecode=404, eres=err("NOT_FOUND", "Hunt not found."),
   errs=[(200, "Success"), (404, "NOT_FOUND")], rules=["Only role addresses published on the site (info@, sales@, contact@) are stored; personal emails are not collected."])

ep(d="Lead Hunter", m="POST", p="/api/v1/prospects/{prospectId}/promote", t="Promote prospect to CRM", auth="session",
   purpose="Create company + contact (role address) as a lead with source lead_hunter.", perm="hunter.use + crm.manage", params="prospectId",
   idem="Repeat returns the same contact.", audit="prospect.promoted", event="contact.created", worker="Graph nodes.",
   req={"owner_id": I("u-usman")},
   code=201, res=ok({"contact_id": I("contact-bright"), "company_id": I("company-bright"), "lifecycle_stage": "lead"}, "2026-10-12T06:10:00Z", "BrightPixel added to CRM."),
   ecode=422, eres=err("SUPPRESSED_CONTACT", "This domain asked not to be contacted."),
   errs=[(201, "Promoted"), (422, "SUPPRESSED_CONTACT")], rules=["Prospect status becomes `promoted`."])

ep(d="Lead Hunter", m="POST", p="/api/v1/prospects/{prospectId}/outreach-draft", t="Draft outreach email", auth="session",
   purpose="'Outreach Email Draft': template-based draft using the prospect's signals; the user edits and sends from their own mailbox.", perm="hunter.use", params="prospectId",
   idem="Read-only computation.", audit="None.", event="None.", worker="None.",
   req={"template": "intro_services", "sender_name": "Usman Tariq", "offer": "website maintenance"},
   code=200, res=ok({"subject": "Website maintenance for BrightPixel", "body": "Hi BrightPixel team,\n\nI saw on your site that you build WordPress sites for marketing clients. Acme Tech handles website maintenance so agencies like yours can focus on clients.\n\nWould a 15-minute call next week be useful?\n\nUsman Tariq\nAcme Tech\n\nIf you prefer not to hear from us, reply 'unsubscribe' and we will not contact you again.",
                     "template": "intro_services", "fields_used": ["company_name", "tech", "sender_name", "offer"], "send_via": "copy_to_mail_client"}, "2026-10-12T06:12:00Z"),
   ecode=422, eres=err("SUPPRESSED_CONTACT", "This domain asked not to be contacted."),
   errs=[(200, "Draft"), (422, "SUPPRESSED_CONTACT")], rules=["Release 1 never sends email automatically; sequences are Release 2 and need INT-003 and an opt-out flow.", "Every draft includes an opt-out line."])

ep(d="Lead Hunter", m="POST", p="/api/v1/suppressions", t="Add to do-not-contact list", auth="session",
   purpose="Record opt-outs and bounces; blocks future promotion and drafts.", perm="hunter.use or crm.manage", params="None",
   idem="Idempotent per (kind, value).", audit="suppression.added", event="suppression.added", worker="Mark matching prospects suppressed.",
   req={"kind": "domain", "value": "adsmiths.example", "reason": "opt_out"},
   code=201, res=ok({"kind": "domain", "stored_as": "sha256", "prospects_suppressed": 1}, "2026-10-12T06:15:00Z"),
   ecode=400, eres=err("VALIDATION_FAILED", "Enter a valid email or domain."),
   errs=[(201, "Added"), (400, "VALIDATION_FAILED")], rules=["Only the SHA-256 of the normalized value is stored."])

# ===================================================================== Automation
RULE = I("rule-stale")
ep(d="Automation and Rules", m="GET", p="/api/v1/rules", t="Automation dashboard", auth="session",
   purpose="'Automation Dashboard': rules, last run and match counts.", perm="rules.manage", params="None",
   idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res=ok({"items": [{"id": RULE, "key": "stale_deal_nudge", "version": 1, "trigger": "deal.stale", "enabled": True, "runs_7d": 14, "matched_7d": 3, "failed_7d": 0}],
                     "external_api_calls_7d": 0}, "2026-10-12T06:00:00Z"),
   ecode=403, eres=err("AUTHORIZATION_DENIED", "Only leadership can manage automations."),
   errs=[(200, "Success"), (403, "AUTHORIZATION_DENIED")], rules=["`external_api_calls_7d` is shown because the product promise is API-light; Release 1 rules make none."])

ep(d="Automation and Rules", m="POST", p="/api/v1/rules", t="Create rule", auth="session",
   purpose="Save a rule definition (new key or new version).", perm="rules.manage", params="None",
   idem="Idempotency-Key required; (key, version) unique.", audit="rule.created", event="rule.created", worker="None.",
   req={"key": "stale_deal_nudge", "definition": {"trigger": "deal.stale", "when": {"all": [{"fact": "deal.days_since_activity", "op": "gte", "value": 14},
        {"any": [{"fact": "deal.stage", "op": "in", "value": ["proposal", "negotiation"]}]}]},
        "then": [{"action": "notify", "to": "owner", "template": "deal_stale"}, {"action": "create_task", "assign": "owner", "title": "Follow up: {deal.title}", "due_in_hours": 24}]}},
   code=201, res=ok({"id": RULE, "key": "stale_deal_nudge", "version": 1, "enabled": True}, "2026-10-01T07:00:00Z", "Rule saved."),
   ecode=400, eres=err("RULE_INVALID", "Fact 'deal.secret' is not available for trigger deal.stale.", details={"reason": "FACT_NOT_ALLOWED:deal.secret"}),
   errs=[(201, "Saved"), (400, "RULE_INVALID (engine/rules.py validate, RUL-03)"), (403, "AUTHORIZATION_DENIED")], rules=["No code, regular expressions or URLs are accepted."])

ep(d="Automation and Rules", m="POST", p="/api/v1/rules/{ruleId}/simulate", t="Simulate rule", auth="session",
   purpose="Run a rule against sample facts; no side effects.", perm="rules.manage", params="ruleId",
   idem="Read-only computation.", audit="None.", event="None.", worker="None.",
   req={"facts": {"deal.days_since_activity": 15, "deal.stage": "proposal", "deal.title": "Website rebuild"}},
   code=200, res=ok({"matched": True, "trace": [{"fact": "deal.days_since_activity", "op": "gte", "value": 14, "actual": 15, "result": True},
                                                 {"fact": "deal.stage", "op": "in", "value": ["proposal", "negotiation"], "actual": "proposal", "result": True}],
                     "actions": [{"action": "notify", "to": "owner", "template": "deal_stale"}, {"action": "create_task", "assign": "owner", "title": "Follow up: Website rebuild", "due_in_hours": 24}]}, "2026-10-12T06:00:00Z"),
   ecode=404, eres=err("NOT_FOUND", "Rule not found."),
   errs=[(200, "Simulated"), (404, "NOT_FOUND")], rules=["Output is exactly engine/rules.py run() (RUL-01)."])

ep(d="Automation and Rules", m="GET", p="/api/v1/rule-runs", t="Workflow execution logs", auth="session",
   purpose="'Workflow Execution Logs and Alerts'.", perm="rules.manage", params="rule_id, outcome, cursor",
   idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res=ok({"items": [{"id": I("run-1"), "rule": "stale_deal_nudge", "event": "deal.stale", "outcome": "matched", "actions": ["notify", "create_task"], "ran_at": "2026-10-12T01:00:00Z"}], "next_cursor": None}, "2026-10-12T06:00:00Z"),
   ecode=403, eres=err("AUTHORIZATION_DENIED", "Only leadership can view automation logs."),
   errs=[(200, "Success"), (403, "AUTHORIZATION_DENIED")], rules=["One run per (rule, event) (DB-12); loops are cut at chain depth 3 (`skipped_loop`)."])

# ===================================================================== Revenue engine and dashboards
ep(d="Revenue Engine and Dashboards", m="GET", p="/api/v1/leakage/findings", t="Revenue leakage findings", auth="session",
   purpose="CEO/CFO list of money at risk with evidence.", perm="leakage.read (CEO, CFO, COO)", params="status, kind, cursor",
   idem="Read-only.", audit="None.", event="None.", worker="Nightly detector run at 01:00 company time.",
   code=200, res=ok({"totals": {"open": 3, "amount_at_risk": "8620.00", "currency": "USD"},
                     "items": [{"id": I("lf-1"), "kind": "overdue_invoice", "label": "INV-2026-1031 overdue 11 days", "amount_at_risk": "6000.00", "currency": "USD", "evidence": {"number": "INV-2026-1031", "days_overdue": 11}, "detected_at": "2026-10-12T20:00:00Z"},
                               {"id": I("lf-2"), "kind": "stale_deal", "label": "Contoso redesign - no activity 17 days", "amount_at_risk": "2500.00", "currency": "USD", "evidence": {"stage": "proposal", "days_without_activity": 17, "weighting": "0.50", "deal_amount": "5000.00"}, "detected_at": "2026-10-12T20:00:00Z"},
                               {"id": I("lf-3"), "kind": "unbilled_time", "label": "Contoso support - 3 h unbilled", "amount_at_risk": "120.00", "currency": "USD", "evidence": {"minutes": 180, "entries": 1}, "detected_at": "2026-10-12T20:00:00Z"}],
                     "note": "Amounts are estimates of money at risk."}, "2026-10-13T04:00:00Z"),
   ecode=403, eres=err("AUTHORIZATION_DENIED", "Only the CEO, CFO and COO can see leakage findings."),
   errs=[(200, "Success"), (403, "AUTHORIZATION_DENIED")], rules=["Detectors and formulas: Section 17 and engine/leakage.py (LEK-01..06)."])

ep(d="Revenue Engine and Dashboards", m="POST", p="/api/v1/leakage/findings/{findingId}/resolve", t="Resolve or dismiss finding", auth="session",
   purpose="Record the action taken (invoiced, followed up, dismissed with reason).", perm="leakage.resolve (CEO, CFO)", params="findingId",
   idem="First resolution wins.", audit="leakage.resolved", event="leakage.resolved", worker="None.",
   req={"resolution": "resolved", "note": "Reminder sent; client promised payment Friday"},
   code=200, res=ok({"id": I("lf-1"), "status": "resolved", "resolved_by": "Omar Siddiqui", "resolved_at": "2026-10-13T05:00:00Z"}, "2026-10-13T05:00:00Z"),
   ecode=409, eres=err("ALREADY_RESOLVED", "This finding was already resolved."),
   errs=[(200, "Resolved"), (400, "VALIDATION_FAILED - note required for dismissed"), (409, "ALREADY_RESOLVED")], rules=["A resolved finding reappears only if its fingerprint changes (new due date, new period)."])

ep(d="Revenue Engine and Dashboards", m="GET", p="/api/v1/dashboards/{role}", t="Role-based dashboard", auth="session",
   purpose="Six dashboard variants (ceo, cto, cfo, coo, hr, employee) with only metrics EMS can source.", perm="dashboards.all for CEO; others only their own role", params="role, period (this_month|last_30_days)",
   idem="Read-only.", audit="None.", event="None.", worker="Cached 5 minutes per org and role.",
   code=200, res=ok({"role": "cfo", "period": {"label": "October 2026", "from": "2026-10-01", "to": "2026-10-31"}, "currency": "USD",
                     "tiles": [{"key": "invoiced", "label": "Invoiced this month", "value": "18450.00", "source": "invoices"},
                               {"key": "collected", "label": "Collected", "value": "11600.00", "source": "payments"},
                               {"key": "outstanding", "label": "Outstanding invoices", "value": "6850.00", "count": 4, "source": "invoices - payments"},
                               {"key": "leakage", "label": "Revenue at risk", "value": "8620.00", "source": "leakage_findings"}],
                     "budget_projects": [{"project": "Northwind website", "budget": "5000.00", "cost_to_date": "1820.00", "ratio": "0.36"}],
                     "unavailable": [{"key": "operating_expenses", "reason": "No accounting integration in Release 1"}, {"key": "net_profit", "reason": "Needs operating expenses"}]}, "2026-10-13T04:00:00Z"),
   ecode=403, eres=err("AUTHORIZATION_DENIED", "You can only open your own role's dashboard."),
   errs=[(200, "Success"), (403, "AUTHORIZATION_DENIED")], rules=["Every tile names its source; a metric without a source is listed under `unavailable` instead of showing sample data (Section 18)."])

ep(d="Revenue Engine and Dashboards", m="GET", p="/api/v1/graph/neighbors", t="Graph memory: related items", auth="session",
   purpose="'Related' panels: people, clients, projects and deals connected to an item.", perm="Results filtered by the caller's read permissions", params="kind, ref_id, depth (1-3)",
   idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res=ok({"node": {"kind": "person", "label": "Bilal Ahmed"},
                     "neighbors": [{"kind": "project", "label": "Northwind website", "depth": 1, "via": ["works_on"]},
                                   {"kind": "client", "label": "Northwind Digital", "depth": 2, "via": ["works_on", "billed_by"]}]}, "2026-10-12T06:00:00Z"),
   ecode=400, eres=err("VALIDATION_FAILED", "Depth must be 1, 2 or 3."),
   errs=[(200, "Success"), (400, "VALIDATION_FAILED"), (404, "NOT_FOUND")], rules=["Backed by ems.graph_neighbors() under RLS (DB-11); no external graph database."])

ep(d="Revenue Engine and Dashboards", m="GET", p="/api/v1/notifications", t="Notifications", auth="session",
   purpose="'Notifications' screen.", perm="Own notifications", params="unread_only, cursor",
   idem="Read-only.", audit="None.", event="None.", worker="None.",
   code=200, res=ok({"items": [{"id": I("n-1"), "kind": "leave.requested", "title": "Bilal Ahmed requested 3 days annual leave", "ref_type": "leave_request", "ref_id": I("lr-bilal"), "read": False, "created_at": "2026-10-12T06:00:00Z"}], "unread": 1, "next_cursor": None}, "2026-10-12T06:05:00Z"),
   ecode=401, eres=err("AUTHENTICATION_REQUIRED", "Your session has expired. Sign in again."),
   errs=[(200, "Success"), (401, "AUTHENTICATION_REQUIRED")], rules=["Delivered in-app in Release 1; email copies need INT-003."])

ep(d="Revenue Engine and Dashboards", m="POST", p="/api/v1/notifications/{notificationId}/read", t="Mark notification read", auth="session",
   purpose="Mark one notification read.", perm="Owner", params="notificationId",
   idem="Idempotent.", audit="None.", event="None.", worker="None.", req={},
   code=200, res=ok({"id": I("n-1"), "read": True}, "2026-10-12T06:06:00Z"),
   ecode=404, eres=err("NOT_FOUND", "Notification not found."),
   errs=[(200, "Marked"), (404, "NOT_FOUND")], rules=["Deleting notifications is not offered; they expire after 90 days."])


# ===================================================================== rendering
def code_block(obj):
    s = obj if isinstance(obj, str) else json.dumps(obj, indent=2, ensure_ascii=False)
    return "\n".join("    " + line for line in s.splitlines()) + "\n"

def tcell(s):
    return str(s).replace("|", "\\|")

def api_id(i):
    return "API-%03d" % i

def render(first):
    out, n = [], len(E)
    out.append(f"# {first}. Release 1 Endpoint Registry - {n} HTTP Operations\n")
    out.append("| ID | Method | Path | Purpose | Auth |\n|---------|--------|----------------------------------------------|------------------------------|-----------|")
    for i, e in enumerate(E, 1):
        out.append(f"| {api_id(i)} | {e['m']} | {tcell(e['p'])} | {tcell(e['t'])} | {tcell(e['auth'])} |")
    out.append("")
    out.append("::: callout-red\nEndpoint result rule\n\nEvery operation shows its request (when it has a body), its success result and at least one error result in the exact envelope the API returns. All people, companies, IDs and amounts are synthetic (fixture in Section 19.4). Frontend and QA work from these examples; an endpoint is not done until its live responses match them in shape, status code and error code.\n:::\n")
    sec, dom = first, None
    for i, e in enumerate(E, 1):
        if e["d"] != dom:
            dom = e["d"]; sec += 1
            out.append(f"# {sec}. {dom} Endpoint Contracts\n")
        out.append(f"## {api_id(i)} {e['t']}\n")
        rows = [("Method", e["m"]), ("Path", e["p"]), ("Purpose", e["purpose"]), ("Auth", e["auth"]), ("Permission", e["perm"]),
                ("Path / query parameters", e["params"]), ("Idempotency / concurrency", e["idem"]), ("Audit", e["audit"]),
                ("Domain event", e["event"]), ("Worker / async", e["worker"])]
        out.append("| Item | Contract |\n|------------------------|--------------------------------------------------------|")
        out += [f"| {k} | {tcell(v)} |" for k, v in rows]
        out.append("")
        if e["req"] is not None:
            out.append("Request example\n"); out.append(code_block(e["req"]))
        out.append(f"Success result ({e['code']})\n"); out.append(code_block(e["res"]))
        for label, code, body in e["extra"]:
            out.append(f"{label} ({code})\n"); out.append(code_block(body))
        out.append(f"Error result ({e['ecode']})\n"); out.append(code_block(e["eres"]))
        out.append("| HTTP | Meaning |\n|------|------------------------------------------------|")
        out += [f"| {c} | {tcell(m)} |" for c, m in e["errs"]]
        out.append("")
        out += [f"-   {tcell(r)}\n" for r in e["rules"]]
    return "\n".join(out), sec, n

def examples():
    return [{"id": api_id(i), "domain": e["d"], "method": e["m"], "path": e["p"], "title": e["t"], "auth": e["auth"],
             "request": e["req"], "success": {"status": e["code"], "body": e["res"]},
             "extra": [{"label": l, "status": c, "body": b} for l, c, b in e["extra"]],
             "error": {"status": e["ecode"], "body": e["eres"]}, "statuses": [c for c, _ in e["errs"]]} for i, e in enumerate(E, 1)]

if __name__ == "__main__":
    md, last, n = render(int(sys.argv[1]))
    open(sys.argv[2], "w").write(md)
    open(sys.argv[3], "w").write(json.dumps(examples(), indent=2))
    print(last, n)
