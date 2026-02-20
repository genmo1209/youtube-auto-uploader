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
# ENV VARIABLES
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
# HINGLISH HOOK ENGINE (AUTO MATCH)
# ==============================

def detect_hook_from_filename(filename):
    name = filename.lower()

    if "karma" in name:
        return "Karma Kabhi Maaf Nahi Karta"
    elif "overthink" in name:
        return "Overthinking Chhodo Warna Nuksaan Hoga"
    elif "anger" in name or "gussa" in name:
        return "Gussa Aapko Barbaad Kar Dega"
    elif "success" in name:
        return "Success Kyun Delay Hota Hai?"
    elif "fear" in name or "dar" in name:
        return "Dar Hi Aapko Rok Raha Hai"
    elif "mind" in name:
        return "Mind Control Nahi Kiya To Life Control Nahi Hogi"
    else:
        default_hooks = [
            "Bhagwan Aapko Test Kyun Karte Hain?",
            "Ye Sach Sunna Zaroori Hai",
            "Aaj Ka Sabse Powerful Pravachan",
            "Zindagi Badal Dene Wali Baat",
            "Is Galti Ki Wajah Se Dukh Milta Hai"
        ]
        return random.choice(default_hooks)

def random_emoji():
    return random.choice(["🔥", "⚡", "🕉️", "🚀", "✨"])

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
                ep = int(match.group(1))
                if ep > max_ep:
                    max_ep = ep

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
    "motivation",
    "hindimotivation",
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
current_episode = get_next_episode()

print(f"🚀 Uploading {len(videos_to_process)} video(s)...")

# ==============================
# PROCESS & UPLOAD
# ==============================

for video in videos_to_process:

    print("\n================================")

    video_id = video["id"]
    video_name = video["name"]

    print("📌 Processing:", video_name)

    try:
        # DOWNLOAD VIDEO
        request = drive_service.files().get_media(fileId=video_id)
        fh = io.FileIO(video_name, "wb")
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.close()

        # AUTO HOOK BASED ON FILENAME
        hook = detect_hook_from_filename(video_name)
        emoji = random_emoji()

        title = f"{hook} | Pravachan Series Ep {current_episode} {emoji} #Shorts"

        description = f"""
🕉️ {hook}
Pravachan Series - Episode {current_episode}

Bhagavad Gita se li gayi powerful seekh.
Agar aap life me clarity chahte hain, ye video end tak dekhiye 🙏

""" + " ".join([f"#{tag}" for tag in hashtags])

        # UPLOAD
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

print("\n🎉 All uploads completed successfully!")
