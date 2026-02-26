import os
import io
import json
import time
import requests
import re

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

GRAPH_URL = "https://graph.facebook.com/v24.0"

# ==============================
# HELPERS
# ==============================

def sanitize_filename(name: str):
    """Remove spaces & special chars (Facebook safe)"""
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", name)
    if safe != name:
        os.rename(name, safe)
    return safe


def check_video_status(video_id):
    """Wait until Facebook processes video"""
    for _ in range(12):  # ~2 minutes max
        r = requests.get(
            f"{GRAPH_URL}/{video_id}",
            params={
                "fields": "status",
                "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
            }
        )

        data = r.json()
        print("Processing status:", data)

        if "status" in data:
            state = data["status"].get("video_status")

            if state == "ready":
                print("✅ Video ready on Facebook")
                return True

            if state == "error":
                print("❌ Facebook processing error")
                return False

        time.sleep(10)

    print("⚠️ Processing timeout (still may publish later)")
    return True


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
# PROCESS VIDEOS
# ==============================

for video in videos_to_process:

    print("\n🎬 Processing:", video["name"])

    local_name = video["name"]

    # --------------------------
    # Download from Drive
    # --------------------------
    request = drive_service.files().get_media(fileId=video["id"])
    fh = io.FileIO(local_name, "wb")
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    local_name = sanitize_filename(local_name)

    try:
        # ==============================
        # PHASE 1 — START
        # ==============================

        start_response = requests.post(
            f"{GRAPH_URL}/{FACEBOOK_PAGE_ID}/video_reels",
            data={
                "upload_phase": "start",
                "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
            },
            timeout=60
        )

        start_result = start_response.json()
        print("START RESPONSE:", start_result)

        if "error" in start_result:
            raise Exception(start_result)

        video_id = start_result["video_id"]
        upload_url = start_result["upload_url"]

        print("Upload session started:", video_id)

        # ==============================
        # PHASE 2 — TRANSFER
        # ==============================

        file_size = os.path.getsize(local_name)

        with open(local_name, "rb") as f:
            transfer_response = requests.post(
                upload_url,
                headers={
                    "Authorization": f"OAuth {FACEBOOK_PAGE_ACCESS_TOKEN}",
                    "offset": "0",
                    "file_size": str(file_size),
                },
                data=f,
                timeout=600
            )

        transfer_result = transfer_response.json()
        print("TRANSFER RESPONSE:", transfer_result)

        if "error" in transfer_result:
            raise Exception(transfer_result)

        print("✅ Video transferred")

        # ==============================
        # PHASE 3 — FINISH
        # ==============================

        finish_response = requests.post(
            f"{GRAPH_URL}/{FACEBOOK_PAGE_ID}/video_reels",
            data={
                "upload_phase": "finish",
                "video_id": video_id,
                "description": "#krishna #bhakti #sanatandharma",
                "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
            },
            timeout=60
        )

        finish_result = finish_response.json()
        print("FINISH RESPONSE:", finish_result)

        if "error" in finish_result:
            raise Exception(finish_result)

        print("✅ Reel submitted:", video_id)

        # ==============================
        # WAIT FOR FACEBOOK PROCESSING
        # ==============================

        if not check_video_status(video_id):
            raise Exception("Facebook processing failed")

    except Exception as e:
        print("❌ Upload Failed:", e)
        os.remove(local_name)
        continue

    # ==============================
    # MOVE FILE AFTER SUCCESS
    # ==============================

    drive_service.files().update(
        fileId=video["id"],
        addParents=UPLOADED_FOLDER_ID,
        removeParents=FOLDER_ID
    ).execute()

    os.remove(local_name)

    print("✅ Moved file to uploaded folder")
    time.sleep(15)

print("\n🎉 Facebook Reel Upload Complete")