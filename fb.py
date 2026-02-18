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

# Take first 4 videos
videos_to_process = files[:4]

print(f"Found {len(videos_to_process)} video(s) to upload.")

# ==============================
# PROCESS VIDEOS
# ==============================

for video in videos_to_process:
    print("\n==============================")
    print("Processing:", video["name"])

    # --------------------------
    # DOWNLOAD VIDEO
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
    title = "Bhagavad Gita Daily Dose"
    description = """Bhagavad Gita Daily Dose – Verse of the Day

#bhakti #devotional #spiritual #krishna
"""

    # --------------------------
    # UPLOAD TO FACEBOOK
    # --------------------------
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
    print("Facebook Response:", result)

    if "error" in result:
        print("❌ Upload failed. Stopping process.")
        os.remove(video["name"])
        exit(1)
    else:
        print("✅ Upload successful.")

    # --------------------------
    # MOVE FILE TO UPLOADED FOLDER
    # --------------------------
    drive_service.files().update(
        fileId=video["id"],
        addParents=UPLOADED_FOLDER_ID,
        removeParents=FOLDER_ID
    ).execute()

    os.remove(video["name"])

    # Optional: small delay to avoid rate limits
    time.sleep(20)

print("\n🎉 All videos processed successfully.")
