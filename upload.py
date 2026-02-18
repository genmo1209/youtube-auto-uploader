import os
import io
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2.credentials import Credentials

# ==============================
# ENV VARIABLES
# ==============================

FOLDER_ID = os.environ["FOLDER_ID"]
UPLOADED_FOLDER_ID = os.environ["UPLOADED_FOLDER_ID"]
REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]

# ==============================
# DRIVE AUTH
# ==============================

service_account_info = json.loads(os.environ["SERVICE_ACCOUNT_JSON"])

drive_creds = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/drive"]
)

drive_service = build("drive", "v3", credentials=drive_creds)

# ==============================
# YOUTUBE AUTH
# ==============================

youtube_creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["https://www.googleapis.com/auth/youtube.upload"]
)

youtube = build("youtube", "v3", credentials=youtube_creds)

# ==============================
# EPISODE COUNTER
# ==============================

if os.path.exists("episode.txt"):
    with open("episode.txt", "r") as f:
        episode_number = int(f.read().strip())
else:
    episode_number = 1

# ==============================
# GET VIDEOS FROM DRIVE
# ==============================

results = drive_service.files().list(
    q=f"'{FOLDER_ID}' in parents and mimeType contains 'video/'",
    orderBy="createdTime asc",
    fields="files(id, name)"
).execute()

files = results.get("files", [])

if not files:
    print("No videos found.")
    exit()

# ==============================
# TAKE FIRST 4 VIDEOS
# ==============================

videos_to_upload = files[:4]

print(f"Found {len(videos_to_upload)} videos to upload")

# ==============================
# PROCESS EACH VIDEO
# ==============================

for video in videos_to_upload:
    print("Processing:", video["name"])

    # DOWNLOAD VIDEO
    request = drive_service.files().get_media(fileId=video["id"])
    fh = io.FileIO(video["name"], "wb")
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    # TITLE & DESCRIPTION
    title = f"Bhagavad Gita Daily Dose – Episode {episode_number}"

    description = """Bhagavad Gita Daily Dose – Verse of the Day

#bhakti #devotional #spiritual #krishna #shorts
"""

    # UPLOAD TO YOUTUBE
    media = MediaFileUpload(video["name"], resumable=True)

    request_upload = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": ["bhakti", "devotional", "gita"],
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": "public"
            }
        },
        media_body=media
    )

    response = request_upload.execute()
    print("YouTube Uploaded:", response["id"])

    # MOVE FILE TO UPLOADED FOLDER
    drive_service.files().update(
        fileId=video["id"],
        addParents=UPLOADED_FOLDER_ID,
        removeParents=FOLDER_ID
    ).execute()

    # DELETE LOCAL FILE
    os.remove(video["name"])

    # INCREASE EPISODE
    episode_number += 1

# ==============================
# SAVE UPDATED EPISODE NUMBER
# ==============================

with open("episode.txt", "w") as f:
    f.write(str(episode_number))

print("All uploads completed successfully.")
