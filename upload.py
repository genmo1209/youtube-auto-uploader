import os
import io
import json
import time
import requests
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

FACEBOOK_PAGE_ID = os.environ["FACEBOOK_PAGE_ID"]
FACEBOOK_PAGE_ACCESS_TOKEN = os.environ["FACEBOOK_PAGE_ACCESS_TOKEN"]
INSTAGRAM_BUSINESS_ID = os.environ["INSTAGRAM_BUSINESS_ID"]

# ==============================
# FACEBOOK UPLOAD
# ==============================

def upload_to_facebook(video_path, title, description):
    print("Uploading to Facebook...")
    url = f"https://graph.facebook.com/v24.0/{FACEBOOK_PAGE_ID}/videos"

    with open(video_path, "rb") as video_file:
        files = {"source": video_file}
        data = {
            "title": title,
            "description": description,
            "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
        }
        response = requests.post(url, files=files, data=data)

    print("Facebook Response:", response.json())

# ==============================
# INSTAGRAM UPLOAD
# ==============================

def upload_to_instagram(video_url, caption):
    print("Uploading to Instagram...")

    container_url = f"https://graph.facebook.com/v24.0/{INSTAGRAM_BUSINESS_ID}/media"
    container_payload = {
        "video_url": video_url,
        "caption": caption,
        "media_type": "REELS",
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
    }

    container_response = requests.post(container_url, data=container_payload).json()

    if "id" not in container_response:
        print("Instagram Container Error:", container_response)
        return

    creation_id = container_response["id"]
    print("Instagram Container Created:", creation_id)

    time.sleep(20)

    publish_url = f"https://graph.facebook.com/v24.0/{INSTAGRAM_BUSINESS_ID}/media_publish"
    publish_payload = {
        "creation_id": creation_id,
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
    }

    publish_response = requests.post(publish_url, data=publish_payload).json()
    print("Instagram Publish Response:", publish_response)

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

videos_to_upload = files[:1]   # 2 videos per run

# ==============================
# MAIN LOOP
# ==============================

for file in videos_to_upload:
    print("Processing:", file["name"])

    # Download file
    request = drive_service.files().get_media(fileId=file["id"])
    fh = io.FileIO(file["name"], "wb")
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    title = f"Bhagavad Gita Daily Dose – Episode {episode_number}"

    description = """Bhagavad Gita Daily Dose – Verse of the Day

#bhakti #devotional #spiritual #krishna #shorts
"""

    # ---------------- YOUTUBE ----------------
    media = MediaFileUpload(file["name"], resumable=True)

    request = youtube.videos().insert(
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

    yt_response = request.execute()
    print("YouTube Uploaded:", yt_response["id"])

    # ---------------- FACEBOOK ----------------
    upload_to_facebook(file["name"], title, description)

    # ---------------- INSTAGRAM ----------------
    drive_service.permissions().create(
        fileId=file["id"],
        body={"type": "anyone", "role": "reader"}
    ).execute()

    public_url = f"https://drive.google.com/uc?export=download&id={file['id']}"
    upload_to_instagram(public_url, description)

    # ---------------- MOVE FILE ----------------
    drive_service.files().update(
        fileId=file["id"],
        addParents=UPLOADED_FOLDER_ID,
        removeParents=FOLDER_ID
    ).execute()

    os.remove(file["name"])
    episode_number += 1

# Save updated episode number
with open("episode.txt", "w") as f:
    f.write(str(episode_number))

print("All uploads completed successfully.")
