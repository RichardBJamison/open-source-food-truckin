# OSFT site server (download gate + contacts)

`python3 serve_site.py --root <site> --port 8930 --data <data-dir>`

Every download signup is:
1. **Saved in the site database**: `<data>/contacts.db` (SQLite, table `contacts`: time, email, os, lang, country, file, hashed IP, user agent). It's also appended to `<data>/signups.csv` as a plain export. Existing CSV rows are imported on first start.
2. **Emailed to the owner**: a notification goes to `me@richardbjamison.com` (set with `OSFT_NOTIFY_TO`). It's queued in the `outbox` table and sent by a background thread, so the download never waits on email or fails because of it. Failures are logged and retried with backoff, up to 8 tries. Mail queued while sending is off stays pending and goes out once credentials are added.

## Email credentials (never commit them)
Set them as env vars, or put the same keys in a git-ignored `<data>/mail.json`:

| Mode | Keys |
|---|---|
| `forwardemail` (same as Open Source Barware) | `FORWARD_EMAIL_USER`, `FORWARD_EMAIL_PASS`, optional `FORWARD_EMAIL_FROM` |
| `smtp` | `OSFT_SMTP_HOST`, `OSFT_SMTP_PORT` (465 SSL / 587 STARTTLS), `OSFT_SMTP_USER`, `OSFT_SMTP_PASS`, `OSFT_SMTP_FROM` |

`OSFT_MAIL_MODE` picks one (`forwardemail`, `smtp` or `off`). By default it uses Forward Email if those credentials are set, then SMTP, and otherwise mail is off.

Queue check: `sqlite3 data/contacts.db "select id,to_addr,status,tries,last_error from outbox"`
