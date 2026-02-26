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

    print("\nProcessing:", video["name"])

    # Download from Drive
    request = drive_service.files().get_media(fileId=video["id"])
    fh = io.FileIO(video["name"], "wb")
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    try:
        # ==============================
        # PHASE 1 — START
        # ==============================

        start_response = requests.post(
            f"https://graph.facebook.com/v24.0/{FACEBOOK_PAGE_ID}/video_reels",
            data={
                "upload_phase": "start",
                "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
            }
        )

        start_result = start_response.json()

        if "error" in start_result:
            raise Exception(start_result)

        video_id = start_result["video_id"]
        upload_url = start_result["upload_url"]

        print("Upload session started:", video_id)

        # ==============================
        # PHASE 2 — TRANSFER
        # ==============================

        file_size = os.path.getsize(video["name"])

        with open(video["name"], "rb") as f:
            transfer_response = requests.post(
                upload_url,
                headers={
                    "Authorization": f"OAuth {FACEBOOK_PAGE_ACCESS_TOKEN}",
                    "offset": "0",
                    "file_size": str(file_size)
                },
                data=f
            )

        transfer_result = transfer_response.json()

        if "error" in transfer_result:
            raise Exception(transfer_result)

        print("Video transferred successfully")

        # ==============================
        # PHASE 3 — FINISH
        # ==============================

        finish_response = requests.post(
            f"https://graph.facebook.com/v24.0/{FACEBOOK_PAGE_ID}/video_reels",
            data={
                "upload_phase": "finish",
                "video_id": video_id,
                "description": "#krishna #bhakti #sanatandharma",
                "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
            }
        )

        finish_result = finish_response.json()

        if "error" in finish_result:
            raise Exception(finish_result)

        print("✅ Uploaded as Facebook Reel:", video_id)

    except Exception as e:
        print("❌ Facebook Reel Upload Failed:", str(e))
        os.remove(video["name"])
        continue

    # Move file after success
    drive_service.files().update(
        fileId=video["id"],
        addParents=UPLOADED_FOLDER_ID,
        removeParents=FOLDER_ID
    ).execute()

    os.remove(video["name"])
    time.sleep(10)

print("\n🎉 Facebook Reel Upload Complete")
