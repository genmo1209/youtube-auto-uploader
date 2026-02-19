import os
import io
import json
import time
import random

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# ==============================
# ENV VARIABLES (CHANNEL 2)
# ==============================

FOLDER_ID = os.environ["FOLDER_ID_CH2"]
UPLOADED_FOLDER_ID = os.environ["UPLOADED_FOLDER_ID_CH2"]

YT_CLIENT_ID = os.environ["YT_CLIENT_ID_CH2"]
YT_CLIENT_SECRET = os.environ["YT_CLIENT_SECRET_CH2"]
YT_REFRESH_TOKEN = os.environ["YT_REFRESH_TOKEN_CH2"]

# ==============================
# GOOGLE DRIVE AUTH
# ==============================

service_account_info = json.loads(os.environ["SERVICE_ACCOUNT_JSON_1"])

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
    refresh_token=YT_REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=YT_CLIENT_ID,
    client_secret=YT_CLIENT_SECRET,
    scopes=["https://www.googleapis.com/auth/youtube.upload"]
)

youtube = build("youtube", "v3", credentials=youtube_creds)

# ==============================
# FETCH VIDEOS FROM DRIVE
# ==============================

print("🔍 Fetching files from Drive...")

results = drive_service.files().list(
    q=f"'{FOLDER_ID}' in parents and trashed=false",
    orderBy="createdTime asc",
    supportsAllDrives=True,
    includeItemsFromAllDrives=True,
    fields="files(id,name,mimeType)"
).execute()

all_files = results.get("files", [])

print("\n📂 DEBUG — Files visible to Service Account:")
for f in all_files:
    print(f["name"], "->", f["mimeType"])

# keep only videos
files = [f for f in all_files if f["mimeType"].startswith("video/")]

if not files:
    print("❌ No videos found.")
    exit()

# ==============================
# PROCESS AND UPLOAD
# ==============================

for i, video in enumerate(videos_to_process, start=1):

    print("\n================================")
    print("📌 Processing:", video["name"])

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
    # DYNAMIC TITLE
    # --------------------------
    title = f"Pravachan Series #{i:02d}"

    # --------------------------
    # DYNAMIC DESCRIPTION + TRENDING HASHTAGS
    # (Combined popular devotional + Gita-related tags)
    # ==============================

    description_base = """Pravachan Series – Spiritual Wisdom and Lessons from the Gita
🙏🙏"""

    hashtags = [
        "#bhakti", "#bhagavadgita", "#krishna", "#spirituality",
        "#hinduism", "#lordkrishna"
    ]

    # Final description with hashtags
    description = f"{description_base}\n\n{' '.join(hashtags)}"

    # ==============================
    # UPLOAD TO YOUTUBE
    # ==============================

    try:
        media = MediaFileUpload(video["name"], resumable=True)

        request_upload = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": hashtags,
                    "categoryId": "22"
                },
                "status": {
                    "privacyStatus": "public"
                }
            },
            media_body=media
        )

        response = request_upload.execute()
        print("✅ Uploaded to YouTube (ID):", response["id"])

    except Exception as e:
        print("❌ Upload failed:", str(e))
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

    # ==============================
    # RANDOM SLEEP (1–5 seconds)
    # ==============================
    gap = random.randint(1, 5)
    print(f"⏱ Sleeping for {gap} seconds…")
    time.sleep(gap)

print("\n🎉 All uploads completed successfully!")
