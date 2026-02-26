import os
import io
import json
import time
import requests

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ==============================
# ENV VARIABLES
# ==============================

FOLDER_ID = os.environ["FOLDER_ID"]
UPLOADED_FOLDER_ID = os.environ["UPLOADED_FOLDER_ID"]

FACEBOOK_PAGE_ID = os.environ["FACEBOOK_PAGE_ID"]
FACEBOOK_PAGE_ACCESS_TOKEN = os.environ["FACEBOOK_PAGE_ACCESS_TOKEN"]

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

    title = "Daily Krishna Wisdom 🙏"
    description = "#krishna #bhakti #sanatandharma"

    try:
    url = f"https://graph.facebook.com/v24.0/{FACEBOOK_PAGE_ID}/video_reels"

    with open(video["name"], "rb") as video_file:
        files_data = {
            "source": video_file
        }

        data = {
            "upload_phase": "finish",
            "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
            "description": "#krishna #bhakti #sanatandharma"
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

    print("✅ Uploaded as Facebook Reel:", result.get("id"))

except Exception as e:
    print("❌ Facebook Reel Upload Failed:", str(e))
    os.remove(video["name"])
    continue

    drive_service.files().update(
        fileId=video["id"],
        addParents=UPLOADED_FOLDER_ID,
        removeParents=FOLDER_ID
    ).execute()

    os.remove(video["name"])
    time.sleep(10)

print("🎉 Facebook Upload Complete")
