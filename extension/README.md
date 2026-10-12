# EMS Chrome extension (Manifest V3)

The Employee Room client from spec Section 9: consent, check-in/out with a task picker, 30-second presence heartbeats,
breaks, the Media Session Page for screen sharing (LiveKit) and settings with "who viewed me".

## Build and load

```bash
npm ci
EMS_ORIGIN=http://localhost:3000 npm run build    # the EMS web app origin (it proxies /api/v1)
npm run typecheck && npm test
```

Load `dist/` with chrome://extensions → Developer mode → Load unpacked (development and staff demo, OD-03).
Set the API's `EXTENSION_ID` to the loaded extension's ID so CORS allows it.

## How it works

| Part | File | Job |
|---|---|---|
| Manifest | `manifest.template.json` | `idle`, `storage`, `alarms`, `cookies`; host permission for the EMS origin only; Chrome 120+ |
| Service worker | `src/background.ts` | 30-second `chrome.alarms` heartbeat (API-019) with `chrome.idle.queryState(300)`; break follow-up; badge `LIVE` while someone views the screen |
| Popup | `src/popup/` | Sign-in (API-003), monitoring notice and consent (API-017), check-in (API-018), break panel (API-021/023), check-out (API-020) |
| Media Session Page | `src/media/` | Screen: `getDisplayMedia({video:{frameRate:5}})`; webcam (if opted in): `getUserMedia` 640x360, at most 10 fps, no audio; publish token (API-024) → one LiveKit room; each stops on breaks, check-out, or Chrome's stop button |
| Settings | `src/settings/` | Account, notice text and consent (with the webcam opt-in), who viewed me live (API-028) |

- Sign-in is shared with the web app: same origin, same cookies. Writes with the session send the `ems_csrf` cookie
  value as `X-CSRF-Token`, which is why the extension needs the `cookies` permission (a deviation from the spec's
  permission list, limited to the EMS origin).
- After check-in, everything for that work session uses the extension token (bearer), which the API revokes at check-out.
- Nothing is recorded; no keystrokes, URLs or microphone. The webcam is shared live only after a separate opt-in.
  Heartbeats report `streaming: false` and `camera: false` during breaks.
- No bundler: TypeScript compiles file by file and the media page loads LiveKit's ES module copied by `build.mjs`.

If someone checks in from the web first, the popup's Check in attaches the extension to that session (fresh token).
