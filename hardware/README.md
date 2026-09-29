# Attendance Kiosk Setup

The attendance kiosk is a browser application at `/kiosk/attendance`. It works with a Raspberry
Pi camera, a USB webcam on a laptop, an Android device camera, or a USB QR reader that types the
decoded value into the fallback field.

## Before You Start

1. Start PostgreSQL, apply migrations and seed the fictional development records.
2. Start the backend and frontend using the commands in the root `README.md`.
3. Sign in as a trainer or institute administrator and open `/attendance`.
4. Register a kiosk device. The device token is displayed once; it is not a user password and the
   server stores only its SHA-256 digest.
5. On the kiosk browser, open `/kiosk/attendance`, enter that token and select **Activate device**.

For production, serve the frontend over HTTPS. Browser camera access requires a secure context,
except on `localhost`. Do not use Chromium's insecure-origin development flag on public networks.

## Raspberry Pi

Recommended hardware is a Raspberry Pi 4 or newer running Raspberry Pi OS Bookworm, with either a
CSI camera or a UVC-compatible USB webcam.

Install Chromium and camera diagnostic tools:

```bash
sudo apt update
sudo apt install -y chromium v4l-utils unclutter
v4l2-ctl --list-devices
```

Open the kiosk in full-screen mode. Replace the example host with the HTTPS hostname of the running
frontend:

```bash
chromium --kiosk --noerrdialogs --disable-session-crashed-bubble \
  --autoplay-policy=no-user-gesture-required \
  https://training.example.test/kiosk/attendance
```

For a controlled local-development network only, Chromium can treat the local HTTP origin as
secure. Replace both occurrences of the address with the actual frontend address:

```bash
chromium --kiosk --noerrdialogs \
  --unsafely-treat-insecure-origin-as-secure=http://192.168.1.20:5173 \
  http://192.168.1.20:5173/kiosk/attendance
```

When serving Vite to another device, start it with a LAN listener and set the API URL first:

```bash
VITE_API_BASE_URL=http://192.168.1.20:8000 npm run dev -- --host 0.0.0.0
```

The backend must also listen on the LAN interface, and its configured CORS origins must explicitly
include the frontend origin:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Laptop With Webcam

1. Open Chrome, Edge or Chromium at `http://localhost:5173/kiosk/attendance` when the app runs on
   the same laptop, or use the deployment's HTTPS URL.
2. Activate the registered device token.
3. Select **Start camera** and allow camera access.
4. Use the full-screen button in the kiosk header or press the browser's full-screen key.
5. If several cameras are connected, select the preferred camera in the browser's site settings.

## Android Device

1. Open the HTTPS kiosk URL in Chrome for Android.
2. Allow camera access when prompted.
3. Activate the device token and add the page to the home screen if a dedicated shortcut is useful.
4. Keep battery optimisation disabled for Chrome during long sessions so the browser is not
   suspended while offline.

Android camera access over a plain LAN HTTP address is normally blocked. Use HTTPS for Android
testing and deployment.

## Daily Operation

1. The trainer creates an attendance session for an assigned programme batch.
2. The trainer opens **Session QR**. The signed code expires after 45 seconds and refreshes every
   30 seconds.
3. The kiosk scans that session QR while online. The validated session is cached locally until its
   attendance window ends.
4. Trainees show the unique QR from `/attendance` in their authenticated account.
5. The kiosk stores every scan in IndexedDB before synchronization. Green feedback means the server
   accepted it; blue means it was already recorded; amber means it is safely queued offline; red
   means server validation rejected it.
6. Trainers open the session report to see timestamps, device codes, inferred absences and approved
   corrections.

## Optional Face Verification Demonstration

Face verification is optional and online-only. QR attendance above remains available to every
trainee, including anyone who declines or withdraws biometric consent.

1. The trainee signs in on their own device, opens `/attendance`, reads the biometric notice,
   actively selects the consent checkbox and completes the three-frame head-turn enrolment.
2. At a paired kiosk, the trainee enters the `NCCT-XXXXXXXX` identity code shown in their attendance
   workspace. The kiosk does not attempt to recognize people standing near the camera.
3. Select **Start face challenge**, enable the camera and follow the movement instruction. Three
   temporary frames are sent to the backend over HTTPS for a match against only that trainee.
4. A high-confidence match records attendance. An uncertain match explicitly says the trainee is
   not yet present and creates an administrator review. A mismatch or failed liveness challenge
   records no attendance. Use the QR fallback when face mode is unavailable or unwanted.
5. Trainees can delete their template from `/attendance`. Institute/NCCT administrators can delete
   it from the session report. Consent and deletion events remain in the audit history.

The included provider is **demonstration mode only**. It uses a coarse image-derived template and
checks frame movement for the head-turn challenge. It does not provide certified face detection or
presentation-attack detection, and a moving photograph or replayed video may pass. Its accuracy and
fairness across demographic groups have not been established. Production configuration therefore
keeps biometrics disabled and rejects the demo provider. A real deployment requires a certified
replaceable provider, legal/privacy review, demographic accuracy and spoof testing, documented
retention, accessible non-biometric service and an incident-response process.

Raw frames are not stored by the application. The database contains an AES-GCM encrypted embedding
plus provider/key metadata; verification history contains only scores and outcomes. Configure
proxies not to capture request bodies and keep the separate biometric encryption key in a managed
secret store. The production container uses temporary memory-backed storage for request spooling.

## Offline/Reconnect Demonstration

Use fictional development accounts and records only.

1. Pair the kiosk to the seeded **Demonstration kiosk check-in** session while online.
2. Disconnect Wi-Fi, unplug Ethernet, or choose **Offline** in Chromium DevTools Network settings.
3. Scan the fictional trainee QR. The kiosk shows **Saved offline** and the pending count becomes 1.
4. Restore connectivity. The browser's `online` event automatically starts synchronization; the
   pending count returns to 0 after server acceptance.
5. Re-send the same queued payload in the automated test or replay the same idempotency key through
   the API. The first response is `created`; the replay is `duplicate` and returns the same
   `check_in_id`.
6. Open the trainer's report. Exactly one attendance row exists for that trainee and session.

Automated proofs are in:

- `frontend/src/lib/kiosk-db.test.ts`: disconnect-style local queue, reconnect sync, queue removal
  and no second client submission.
- `backend/tests/test_attendance.py`: repeated delivery of the identical idempotency key returns the
  same check-in and leaves one database row.

Run them with:

```bash
npm test --workspace @ncct/frontend -- kiosk-db.test.ts
cd backend
.venv/bin/pytest tests/test_attendance.py -q
```

## Troubleshooting

- **Camera unavailable:** check browser site permissions and `v4l2-ctl --list-devices`; camera
  access also fails on non-secure origins other than `localhost`.
- **Session QR rejected:** refresh the trainer QR and confirm the kiosk belongs to the programme's
  institution.
- **Attendance remains pending:** restore connectivity, verify the API health endpoint and select
  **Synchronize now**.
- **Rejected queue item:** read the red validation reason. Typical causes are an inactive account,
  wrong programme or batch, cancelled session, expired attendance window or invalid trainee QR.
- **Device revoked:** register a replacement from `/attendance`; a revoked device token cannot pair
  or synchronize.
