import os
import io
import json
import time
import random
from datetime import datetime

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# ==============================
# ENV VARIABLES
# ==============================

FOLDER_ID = os.environ["FOLDER_ID"]
UPLOADED_FOLDER_ID = os.environ["UPLOADED_FOLDER_ID"]

REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]

VIDEOS_PER_RUN = int(os.environ.get("VIDEOS_PER_RUN", 4))

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
    scopes=["https://www.googleapis.com/auth/youtube"]
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
# TITLE SYSTEM
# ==============================

title_hooks = [
    "Stop Scrolling – Krishna Is Speaking To You",
    "This Krishna Message Will Change Your Life",
    "One Gita Line That Hits Different",
    "Krishna’s Powerful Advice for Tough Times",
    "Life Changing Gita Wisdom"
]

tags = [
    "bhagavadgita", "krishna", "radhakrishna",
    "bhakti", "spirituality", "sanatandharma",
    "motivation", "lifequotes", "shorts"
]

# ==============================
# FETCH VIDEOS
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

videos_to_process = files[:VIDEOS_PER_RUN]

# ==============================
# PROCESS
# ==============================

for video in videos_to_process:

    print("Processing:", video["name"])

    request = drive_service.files().get_media(fileId=video["id"])
    fh = io.FileIO(video["name"], "wb")
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    title = f"{random.choice(title_hooks)} | Episode {episode_number}"

    description = f"""
Daily Krishna Wisdom 🙏

Ancient knowledge for modern success.

#shorts #krishna #bhagavadgita
"""

    try:
        media = MediaFileUpload(video["name"], resumable=True)

        request_upload = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "categoryId": "22"
                },
                "status": {
                    "privacyStatus": "public"
                }
            },
            media_body=media
        )

        response = request_upload.execute()
        video_id = response["id"]

        print("✅ Uploaded to YouTube:", video_id)

    except Exception as e:
        print("❌ YouTube Upload Failed:", str(e))
        os.remove(video["name"])
        continue

    drive_service.files().update(
        fileId=video["id"],
        addParents=UPLOADED_FOLDER_ID,
        removeParents=FOLDER_ID
    ).execute()

    os.remove(video["name"])

    episode_number += 1
    time.sleep(15)

with open("episode.txt", "w") as f:
    f.write(str(episode_number))

print("🎉 YouTube Upload Complete")
