import os
import io
import json
import time
import requests
import re
import random

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from pytrends.request import TrendReq

# ==============================
# ENV VARIABLES
# ==============================

SOURCE_FOLDER_ID = os.environ["UPLOADED_FOLDER_ID_CH3"]
DEST_FOLDER_ID = os.environ["UPLOADED_FB_PYSCHO"]

FB_PAGE_ID = os.environ["FB_PAGE_ID"]
FB_PAGE_TOKEN = os.environ["FB_PAGE_TOKEN"]

SERVICE_ACCOUNT_JSON = os.environ["SERVICE_ACCOUNT_JSON"]

VIDEOS_PER_RUN = int(os.environ.get("VIDEOS_PER_RUN", 1))

GRAPH_URL = "https://graph.facebook.com/v24.0"

# ==============================
# TRENDING HOOK + HASHTAG SYSTEM
# ==============================

HOOK_TEMPLATES = [
    "The hidden psychology behind {topic} 🤯",
    "Nobody talks about this truth about {topic} 😳",
    "Why your brain reacts like this to {topic} 🧠",
    "The science of {topic} explained in 20 seconds",
    "This is why {topic} controls your life 😱",
]

BASE_HASHTAGS = [
    "#Psychology", "#Mindset", "#SelfGrowth",
    "#MentalHealth", "#HumanBehavior",
    "#DailyWisdom", "#ReelsIndia", "#ViralReels"
]

def generate_trending_caption():
    try:
        pytrends = TrendReq()
        trends = pytrends.trending_searches(pn='india')[0].tolist()

        topic = random.choice(trends[:20])
        hook = random.choice(HOOK_TEMPLATES).format(topic=topic)

        trending_tags = [
            f"#{t.replace(' ', '')}" for t in random.sample(trends[:20], 5)
        ]

        base_tags = random.sample(BASE_HASHTAGS, 4)

        hashtags = " ".join(trending_tags + base_tags)

        return hook, hashtags

    except:
        topic = "overthinking"
        hook = random.choice(HOOK_TEMPLATES).format(topic=topic)
        hashtags = " ".join(random.sample(BASE_HASHTAGS, 5))
        return hook, hashtags

# ==============================
# GOOGLE DRIVE AUTH
# ==============================

service_account_info = json.loads(SERVICE_ACCOUNT_JSON)

drive_creds = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/drive"]
)

drive_service = build("drive", "v3", credentials=drive_creds)

# ==============================
# FETCH VIDEOS
# ==============================

results = drive_service.files().list(
    q=f"'{SOURCE_FOLDER_ID}' in parents and mimeType contains 'video/'",
    orderBy="createdTime asc",
    fields="files(id, name)",
    supportsAllDrives=True,
    includeItemsFromAllDrives=True
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

    local_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", video["name"])

    # --------------------------
    # DOWNLOAD FROM DRIVE
    # --------------------------
    request = drive_service.files().get_media(
        fileId=video["id"],
        supportsAllDrives=True
    )

    fh = io.FileIO(local_name, "wb")
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    fh.close()

    try:
        # ==============================
        # PHASE 1 — START
        # ==============================

        start_response = requests.post(
            f"{GRAPH_URL}/{FB_PAGE_ID}/video_reels",
            data={
                "upload_phase": "start",
                "access_token": FB_PAGE_TOKEN
            },
            timeout=60
        )

        start_result = start_response.json()
        print("START RESPONSE:", start_result)

        if "error" in start_result:
            raise Exception(start_result)

        video_id = start_result["video_id"]
        upload_url = start_result["upload_url"]

        print("✅ Upload session started:", video_id)

        # ==============================
        # PHASE 2 — TRANSFER
        # ==============================

        file_size = os.path.getsize(local_name)

        with open(local_name, "rb") as f:
            transfer_response = requests.post(
                upload_url,
                headers={
                    "Authorization": f"OAuth {FB_PAGE_TOKEN}",
                    "offset": "0",
                    "file_size": str(file_size),
                },
                data=f,
                timeout=600
            )

        print("TRANSFER RESPONSE:", transfer_response.text)

        transfer_result = transfer_response.json()

        if "error" in transfer_result:
            raise Exception(transfer_result)

        print("✅ Video transferred")

        # ==============================
        # PHASE 3 — FINISH (UNPUBLISHED)
        # ==============================

        title, hashtags = generate_trending_caption()

        finish_response = requests.post(
            f"{GRAPH_URL}/{FB_PAGE_ID}/video_reels",
            data={
                "upload_phase": "finish",
                "video_id": video_id,

                # ✅ Visible in Business Suite & Mobile
                "published": "false",

                "description": f"{title}\n\n{hashtags}",
                "access_token": FB_PAGE_TOKEN
            },
            timeout=60
        )

        print("FINISH RESPONSE:", finish_response.text)

        finish_result = finish_response.json()

        if "error" in finish_result:
            raise Exception(finish_result)

        print("✅ Reel uploaded as UNPUBLISHED:", video_id)

    except Exception as e:
        print("❌ Upload Failed:", e)
        os.remove(local_name)
        continue

    # ==============================
    # MOVE FILE TO UPLOADED_FB_PYSCHO
    # ==============================

    drive_service.files().update(
        fileId=video["id"],
        addParents=DEST_FOLDER_ID,
        removeParents=SOURCE_FOLDER_ID,
        supportsAllDrives=True
    ).execute()

    os.remove(local_name)

    print("✅ File moved to UPLOADED_FB_PYSCHO")
    time.sleep(10)

print("\n🎉 Reel Upload Complete (Ready for Manual Publish)")
