import os
import io
import json
import time
import requests

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# ==============================
# ENV VARIABLES
# ==============================

FOLDER_ID = os.environ["FOLDER_ID"]
UPLOADED_FOLDER_ID = os.environ["UPLOADED_FOLDER_ID"]

# YouTube
REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]

# Facebook
FACEBOOK_PAGE_ID = os.environ["FACEBOOK_PAGE_ID"]
FACEBOOK_PAGE_ACCESS_TOKEN = os.environ["FACEBOOK_PAGE_ACCESS_TOKEN"]

# ==============================
# GOOGLE DRIVE AUTH
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
# FETCH VIDEOS FROM DRIVE
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

videos_to_process = files[:4]
print(f"Found {len(videos_to_process)} video(s)")

# ==============================
# PROCESS EACH VIDEO
# ==============================

for video in videos_to_process:

    print("\n==============================")
    print("Processing:", video["name"])

    # --------------------------
    # DOWNLOAD FROM DRIVE
    # --------------------------
    request = drive_service.files().get_media(fileId=video["id"])
    fh = io.FileIO(video["name"], "wb")
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    # --------------------------
    # VIDEO META
    # --------------------------
    title = f"Bhagavad Gita Daily Dose – Episode {episode_number}"
    description = """Bhagavad Gita Daily Dose – Verse of the Day

#bhakti #devotional #spiritual #krishna #shorts
"""

    # ==============================
    # 1️⃣ UPLOAD TO YOUTUBE
    # ==============================

    try:
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
        print("✅ YouTube Uploaded:", response["id"])

    except Exception as e:
        print("❌ YouTube Upload Failed:", str(e))
        os.remove(video["name"])
        continue

    # ==============================
    # 2️⃣ UPLOAD TO FACEBOOK
    # ==============================

    try:
        url = f"https://graph.facebook.com/v24.0/{FACEBOOK_PAGE_ID}/videos"

        with open(video["name"], "rb") as video_file:
            files_data = {"source": video_file}
            data = {
                "title": title,
                "description": description,
                "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
            }

            response = requests.post(
                url,
                files=files_data,
                data=data,
                timeout=300
            )

        result = response.json()

        if "error" in result:
            raise Exception(result)

        print("✅ Facebook Uploaded:", result.get("id"))

    except Exception as e:
        print("❌ Facebook Upload Failed:", str(e))
        os.remove(video["name"])
        continue

    # ==============================
    # MOVE FILE TO UPLOADED FOLDER
    # ==============================

    drive_service.files().update(
        fileId=video["id"],
        addParents=UPLOADED_FOLDER_ID,
        removeParents=FOLDER_ID
    ).execute()

    os.remove(video["name"])

    episode_number += 1
    time.sleep(15)

# ==============================
# SAVE EPISODE NUMBER
# ==============================

with open("episode.txt", "w") as f:
    f.write(str(episode_number))

print("\n🎉 All uploads completed successfully.")
