import os

from django.conf import settings

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def is_enabled():
    return getattr(settings, "GOOGLE_DOCS_ENABLED", False)


def _save_credentials(creds):
    with open(settings.GOOGLE_TOKEN_FILE, "w", encoding="utf-8") as handle:
        handle.write(creds.to_json())


def _load_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    token_file = settings.GOOGLE_TOKEN_FILE
    if not os.path.exists(token_file):
        return None
    creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_credentials(creds)
    return creds


def has_credentials():
    creds = _load_credentials()
    return bool(creds and creds.valid)


def build_flow(redirect_uri):
    from google_auth_oauthlib.flow import Flow

    return Flow.from_client_secrets_file(
        settings.GOOGLE_CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )


def store_credentials_from_flow(flow):
    _save_credentials(flow.credentials)


def upload_docx_as_gdoc(docx_bytes, title):
    """Upload a .docx byte string to Drive, converting it to a Google Doc.

    Returns the document's shareable link, or None if not authorized yet.
    """
    from io import BytesIO

    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload

    creds = _load_credentials()
    if not creds or not creds.valid:
        return None

    service = build("drive", "v3", credentials=creds)
    media = MediaIoBaseUpload(
        BytesIO(docx_bytes),
        mimetype=(
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
        resumable=False,
    )
    metadata = {
        "name": title,
        "mimeType": "application/vnd.google-apps.document",
    }
    created = (
        service.files()
        .create(body=metadata, media_body=media, fields="id, webViewLink")
        .execute()
    )
    return created.get("webViewLink")
