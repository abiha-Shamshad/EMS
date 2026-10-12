-- EMS Release 1 migration 006: webcam in the Employee Room (product owner decision, 2026-10-13).
-- This extends spec Section 9.1, which listed webcam as never collected. The safeguards of live screen sharing apply:
--   * separate opt-in: stream_consents.webcam is true only when the employee ticked the webcam consent for this notice;
--   * live only while checked in, never recorded, paused on breaks, no microphone;
--   * gated by organizations.live_view_enabled (OD-02: the legal review must now cover the webcam as well);
--   * every view is logged in stream_views with a reason and shown to the employee.
-- Same conventions as 001-005. Run after 005 as an admin role.

RESET ROLE;
SET ROLE ems_owner;
SET search_path = ems, public;

ALTER TABLE stream_consents ADD COLUMN webcam boolean NOT NULL DEFAULT false;   -- webcam opt-in for this notice version
ALTER TABLE work_sessions ADD COLUMN camera boolean NOT NULL DEFAULT false;     -- the webcam is being published right now

RESET ROLE;
