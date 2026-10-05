# Timezone Policy

The classroom is in Cambodia (`Asia/Phnom_Penh`, UTC+7, no daylight saving).
The cloud server (Render) runs on UTC, so the code never relies on the server
clock. All helpers live in `backend/app/core/timezone.py`.

## Two kinds of stored times

| Kind | Stored as | Examples | Created with | Shown with |
|---|---|---|---|---|
| Classroom time | naive Cambodia wall clock | session start/late/close, attendance `first_seen_time`, attendance event `timestamp`, weekly schedules | `classroom_now()`, `classroom_today()` | as-is |
| Audit time | naive UTC | `created_at`, `updated_at`, `last_seen`, recording start/stop, Edge `captured_at` | `utc_now()` | `kh_datetime` / `kh_time` template filters |

## Rules

- Attendance status (P / L / A, after close) compares a check-in with the
  session times, so every check-in is converted to classroom time first.
  The Edge Agent sends `captured_at` in UTC; the server converts it with
  `to_classroom_time()`.
- Never call `datetime.now()` or `date.today()` in app code.
- CSV exports label converted audit columns `*_cambodia`.
