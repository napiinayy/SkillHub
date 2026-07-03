# SkillHub — CV Builder

A small Django app that stores all your skills, experiences, and achievements in
one place so you can assemble a tailored CV in a few clicks. Manage everything
in the Django admin, filter by category or date, **preview the CV live**, export
an editable **.docx**, and save selections as reusable **presets**. An optional
one-click **Google Docs** export is included.

---

## 1. Requirements

- Python 3.10+ (3.11 or 3.12 recommended)
- `pip` and a terminal
- (Optional) A Google account + Google Cloud project for Google Docs export

## 2. Setup (local)

Open a terminal in the project folder (the one containing `manage.py`).

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 3. Initialize the database and create your login

```bash
python manage.py makemigrations cv
python manage.py migrate
python manage.py createsuperuser
```

Follow the prompts to set a username, email, and password.

## 4. Run it

```bash
python manage.py runserver
```

Then open:

- **Admin (add/edit/delete skills):** http://127.0.0.1:8000/admin/
- **CV Builder:** http://127.0.0.1:8000/

Log in with the superuser you just created.

---

## 5. How to use

1. **Add your data** in the admin under *Entries*. Each entry has a name,
   category (Work Experience / Campus Organization / Certificate),
   organization, start/end dates, and description. Add **Achievements** directly
   on an entry — they belong to that entry.
2. **Open the CV Builder.** Use the **Filter** (category + date range) to narrow
   the list, then tick the entries and achievements you want.
3. **Choose an achievement layout** — nested under each experience, or grouped
   into one Achievements section. You decide this per CV.
4. **Preview** to see the exact CV rendered live on the page before you commit.
5. **Export .docx** to download an editable Word document, **Save preset** to
   store the selection, or (if enabled) **Save to Google Docs**.
6. **Reuse a preset** any time from *Saved presets* — one click to regenerate
   the same CV as a .docx (or push it to Google Docs).

---

## 6. Optional: Google Docs export

This uploads the generated CV to your Google Drive, converts it to a Google Doc,
and opens it. It is **off by default**.

1. Go to the Google Cloud Console (https://console.cloud.google.com/), create a
   project, and enable the **Google Drive API**.
2. Configure the **OAuth consent screen** (External is fine; add your own Google
   account under *Test users*).
3. Create an **OAuth client ID** of type **Web application**, and add this
   authorized redirect URI:
   ```
   http://127.0.0.1:8000/google/callback/
   ```
4. Download the client-secret JSON and save it in the project folder as
   `client_secret.json`.
5. Copy `.env.example` to `.env` and set:
   ```
   GOOGLE_DOCS_ENABLED=True
   GOOGLE_CLIENT_SECRETS_FILE=client_secret.json
   ```
6. Restart the server. A **Save to Google Docs** button now appears. The first
   time you use it you'll go through Google sign-in; after that a token is cached
   in `google_token.json`.

> For local http testing, `OAUTHLIB_INSECURE_TRANSPORT=1` is set automatically
> when `DEBUG=True`.

---

## 7. Configuration (.env)

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Django secret key (use a random value in production) |
| `DEBUG` | `True` for local dev, `False` in production |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated https origins for production |
| `DATABASE_URL` | Leave blank for local SQLite; set for Postgres |
| `GOOGLE_DOCS_ENABLED` | `True` to enable Google Docs export |

---

## 8. Deploy (use from anywhere)

The app runs on any host that supports Django (Render, Railway, Fly.io).

1. Push the project to GitHub.
2. Create a web service from the repo. Build command:
   `pip install -r requirements.txt`. Start command: `gunicorn skillhub.wsgi`.
   The included `Procfile` also runs `migrate` on release.
3. Add a **PostgreSQL** database (the host provides `DATABASE_URL`).
4. Set env vars: `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS=your-domain`,
   `CSRF_TRUSTED_ORIGINS=https://your-domain`.
5. For Google Docs in production, add `https://your-domain/google/callback/` as
   an authorized redirect URI in Google Cloud.

---

## 9. Project layout

```
skillhub/
  manage.py            # Django entry point
  requirements.txt
  Procfile             # for Render/Railway
  .env.example
  README.md
  skillhub/            # project config (settings, urls, wsgi, asgi)
  cv/                  # the app
    models.py          # Entry, Achievement, CVPreset
    admin.py           # admin CRUD + filters
    views.py           # builder UI, live preview, exports
    cv_render.py       # HTML CV preview renderer
    docx_export.py     # .docx generator
    google_export.py   # optional Google Docs upload
    urls.py
```

---

## 10. Troubleshooting

- **`no such table`** — run `python manage.py migrate`.
- **Admin looks unstyled after deploy** — run `python manage.py collectstatic`.
- **Google button missing** — `GOOGLE_DOCS_ENABLED` must be `True` and the
  server restarted.
- **Google redirect error** — the redirect URI in Google Cloud must exactly
  match `http://127.0.0.1:8000/google/callback/`.

## Tip

Set your real first/last name on your admin user (Admin → Users) so the CV
header shows your name instead of your username.
