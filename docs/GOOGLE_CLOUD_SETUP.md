# Google Cloud / Gemini setup

Needed before Phase 3 onward can do anything real.

## 1. Gemini API key

1. Go to https://aistudio.google.com/app/apikey
2. Create an API key.
3. Put it in `.env` as `GEMINI_API_KEY`.

(For production-scale usage, consider Vertex AI instead of the AI Studio key — same model,
billed through your GCP project, higher rate limits.)

## 2. Google Cloud project + OAuth client (Gmail / Sheets / Drive)

1. Create a project at https://console.cloud.google.com/
2. APIs & Services → Library → enable:
   - Gmail API
   - Google Sheets API
   - Google Drive API
3. APIs & Services → OAuth consent screen:
   - User type: Internal (if using Google Workspace) or External + add the sending account as a
     test user while in development.
   - Scopes needed (minimum necessary, matching what the backend will request):
     - `https://www.googleapis.com/auth/gmail.send`
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/spreadsheets`
     - `https://www.googleapis.com/auth/drive.file`
4. APIs & Services → Credentials → Create Credentials → OAuth client ID:
   - Application type: Web application
   - Authorized redirect URI: `http://localhost:8000/api/integrations/google/callback`
     (matches `GOOGLE_OAUTH_REDIRECT_URI` in `.env.example`; update both together for prod)
5. Copy the Client ID and Client Secret into `.env` as `GOOGLE_OAUTH_CLIENT_ID` /
   `GOOGLE_OAUTH_CLIENT_SECRET`.

## 3. Token encryption key

Generate once and keep it stable (rotating it invalidates every stored OAuth token):

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Put the output in `.env` as `TOKEN_ENCRYPTION_KEY`.

## 4. Search provider for lead discovery

1. Create a Programmable Search Engine at https://programmablesearchengine.google.com/
   - Set it to search the entire web (not just specific sites).
2. Get an API key for the Custom Search JSON API from
   https://console.cloud.google.com/apis/library/customsearch.googleapis.com
3. Put the engine ID and API key in `.env` as `GOOGLE_CSE_ENGINE_ID` / `GOOGLE_CSE_API_KEY`.

## 5. Crawl4AI

Crawl4AI is in `requirements.txt`. After `pip install`, it needs a one-time Playwright browser
install:

```bash
playwright install --with-deps chromium
```

The Docker image already runs this step.

## Production notes

- Move from the AI Studio Gemini key to a Vertex AI service account before going to production —
  better quota, billing visibility, and it keeps the credential inside your GCP IAM boundary
  instead of a loose API key.
- The OAuth consent screen needs Google verification before going to "External" + production
  mode if you request sensitive scopes like `gmail.send` for non-test users outside your
  organisation.
- Use Cloud Run environment variables / Secret Manager for all of the above in deployment — never
  bake them into the image.
