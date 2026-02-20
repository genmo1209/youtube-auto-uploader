import os
import io
import json
import time
import random
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
    scopes=["https://www.googleapis.com/auth/youtube.upload"]
)

youtube = build("youtube", "v3", credentials=youtube_creds)

# ==============================
# VIRAL TITLE ENGINE
# ==============================

viral_hooks = [
    "Krishna Says: Stop Overthinking",
    "This Karma Truth Will Shock You",
    "Why God Delays Your Success",
    "The Truth About Your Suffering",
    "This Message Will Change You",
    "If You Feel Lost, Watch This",
    "Most People Ignore This Lesson",
    "Your Mind Is Your Biggest Enemy",
    "Don’t Skip This Spiritual Message",
    "This One Habit Is Ruining Your Life"
]

emojis = ["⚡", "🔥", "✨", "🚀", "💡", "🕉️"]

def generate_title():
    hook = random.choice(viral_hooks)
    emoji = random.choice(emojis)
    return f"{hook} {emoji} #Shorts"

# ==============================
# HASHTAG ENGINE
# ==============================

hashtag_groups = [
    ["krishna", "bhagavadgita", "sanatandharma", "hinduism"],
    ["spirituality", "mindset", "karma", "innerpeace"],
    ["motivation", "lifequotes", "wisdom", "selfgrowth"],
    ["devotional", "bhakti", "godmessage", "dailywisdom"]
]

shorts_boost_tags = ["shorts", "ytshorts", "viralshorts"]

def generate_hashtags():
    group = random.choice(hashtag_groups)
    all_tags = list(set(group + shorts_boost_tags))
    return all_tags

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

print(f"📂 Total files found: {len(all_files)}")

video_files = [
    f for f in all_files
    if f.get("mimeType", "").startswith("video/")
]

if not video_files:
    print("❌ No videos found.")
    exit()

print(f"🎬 Video files found: {len(video_files)}")

videos_to_process = video_files[:4]

print(f"\n🚀 Preparing to upload {len(videos_to_process)} video(s)...")

# ==============================
# PROCESS AND UPLOAD
# ==============================

for video in videos_to_process:

    print("\n================================")

    video_id = video.get("id")
    video_name = video.get("name")

    print("📌 Processing:", video_name)

    try:
        # --------------------------
        # DOWNLOAD VIDEO
        # --------------------------
        request = drive_service.files().get_media(fileId=video_id)
        fh = io.FileIO(video_name, "wb")
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.close()

        # --------------------------
        # GENERATE TITLE & HASHTAGS
        # --------------------------
        title = generate_title()
        hashtags = generate_hashtags()

        description_base = """
🕉️ Daily Krishna Spiritual Wisdom
Transform Your Mind. Transform Your Life.

Watch till the end for a powerful life-changing message 🙏
"""

        description = f"{description_base}\n\n" + " ".join(
            [f"#{tag}" for tag in hashtags]
        )

        # --------------------------
        # UPLOAD TO YOUTUBE (RESUMABLE)
        # --------------------------
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

        print("✅ Uploaded to YouTube (ID):", response.get("id"))

        # --------------------------
        # MOVE FILE TO UPLOADED FOLDER
        # --------------------------
        drive_service.files().update(
            fileId=video_id,
            addParents=UPLOADED_FOLDER_ID,
            removeParents=FOLDER_ID
        ).execute()

        os.remove(video_name)

        # --------------------------
        # RANDOM GAP
        # --------------------------
        gap = random.randint(3, 7)
        print(f"⏱ Sleeping for {gap} seconds...")
        time.sleep(gap)

    except Exception as e:
        print("❌ Error processing video:", str(e))
        traceback.print_exc()

        if os.path.exists(video_name):
            os.remove(video_name)

        continue

print("\n🎉 All uploads completed successfully!")
