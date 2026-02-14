import os
import io
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2.credentials import Credentials

FOLDER_ID = os.environ["FOLDER_ID"]
UPLOADED_FOLDER_ID = os.environ["UPLOADED_FOLDER_ID"]
REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]

# ---- DRIVE AUTH
service_account_info = json.loads(os.environ["SERVICE_ACCOUNT_JSON"])
drive_creds = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/drive"]
)
drive_service = build("drive", "v3", credentials=drive_creds)

# ---- YOUTUBE AUTH
youtube_creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["https://www.googleapis.com/auth/youtube.upload"]
)
youtube = build("youtube", "v3", credentials=youtube_creds)

# ---- GET VIDEOS
results = drive_service.files().list(
    q=f"'{FOLDER_ID}' in parents and mimeType contains 'video/'",
    fields="files(id, name, parents)"
).execute()

files = results.get("files", [])

if not files:
    print("No videos found.")
    exit()

for file in files:
    print("Processing:", file["name"])

    request = drive_service.files().get_media(fileId=file["id"])
    fh = io.FileIO(file["name"], "wb")
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    media = MediaFileUpload(file["name"], resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": file["name"],
                "description": "Auto uploaded #shorts",
                "tags": ["shorts"],
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": "public"
            }
        },
        media_body=media
    )

    response = request.execute()
    print("Uploaded:", response["id"])

    # Move file to uploaded folder
    drive_service.files().update(
        fileId=file["id"],
        addParents=UPLOADED_FOLDER_ID,
        removeParents=FOLDER_ID,
        fields="id, parents"
    ).execute()

    print("Moved to uploaded folder")

    os.remove(file["name"])
