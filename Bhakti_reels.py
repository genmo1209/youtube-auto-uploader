import os
import io
import json
import time
import random
import re
import traceback

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
    token=None,
    refresh_token=YT_REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=YT_CLIENT_ID,
    client_secret=YT_CLIENT_SECRET,
    scopes=[
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly"
    ]
)

youtube = build("youtube", "v3", credentials=youtube_creds)

# ==============================
# DYNAMIC HOOK ENGINE
# ==============================

hooks = [
    "Why God Tests You",
    "This Karma Truth Will Shock You",
    "Stop Overthinking Now",
    "The Truth About Your Suffering",
    "Why You Feel Stuck in Life",
    "Krishna’s Powerful Advice",
    "Most People Ignore This Lesson",
    "If You Feel Lost, Watch This",
    "This One Habit Is Ruining You",
    "Your Mind Is Your Biggest Enemy"
]

emojis = ["🔥", "⚡", "🕉️", "✨", "🚀"]

def generate_hook():
    return random.choice(hooks)

def generate_emoji():
    return random.choice(emojis)

# ==============================
# GET NEXT EPISODE NUMBER
# ==============================

def get_next_episode():
    try:
        request = youtube.search().list(
            part="snippet",
            forMine=True,
            order="date",
            maxResults=25,
            type="video"
        )
        response = request.execute()

        max_ep = 0

        for item in response.get("items", []):
            title = item["snippet"]["title"]
            match = re.search(r"Ep\s*(\d+)", title, re.IGNORECASE)
            if match:
                ep_num = int(match.group(1))
                if ep_num > max_ep:
                    max_ep = ep_num

        return max_ep + 1

    except Exception:
        return 1

# ==============================
# HASHTAGS
# ==============================

hashtags = [
    "pravachan",
    "krishna",
    "bhagavadgita",
    "sanatandharma",
    "spirituality",
    "shorts",
    "ytshorts"
]

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

video_files = [
    f for f in results.get("files", [])
    if f.get("mimeType", "").startswith("video/")
]

if not video_files:
    print("❌ No videos found.")
    exit()

videos_to_process = video_files[:4]

print(f"🚀 Uploading {len(videos_to_process)} video(s)...")

# ==============================
# PROCESS & UPLOAD
# ==============================

current_episode = get_next_episode()

for video in videos_to_process:

    print("\n================================")

    video_id = video["id"]
    video_name = video["name"]

    print("📌 Processing:", video_name)

    try:
        # DOWNLOAD
        request = drive_service.files().get_media(fileId=video_id)
        fh = io.FileIO(video_name, "wb")
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.close()

        # GENERATE TITLE
        hook = generate_hook()
        emoji = generate_emoji()

        title = f"{hook} | Pravachan Series Ep {current_episode} {emoji} #Shorts"

        description = f"""
🕉️ {hook}
Pravachan Series - Episode {current_episode}

Daily Spiritual Wisdom from Bhagavad Gita.
Watch till the end for powerful life guidance 🙏

""" + " ".join([f"#{tag}" for tag in hashtags])

        # UPLOAD (RESUMABLE)
        media = MediaFileUpload(video_name, resumable=True)

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

        response = None
        while response is None:
            status, response = request_upload.next_chunk()
            if status:
                print(f"📤 Upload progress: {int(status.progress() * 100)}%")

        print("✅ Uploaded:", title)

        # MOVE FILE
        drive_service.files().update(
            fileId=video_id,
            addParents=UPLOADED_FOLDER_ID,
            removeParents=FOLDER_ID
        ).execute()

        os.remove(video_name)

        current_episode += 1

        time.sleep(random.randint(3, 7))

    except Exception as e:
        print("❌ Error:", str(e))
        traceback.print_exc()

        if os.path.exists(video_name):
            os.remove(video_name)

        continue

print("\n🎉 All uploads completed!")
