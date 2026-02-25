import os
import io
import json
import time
import random
import requests
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

FACEBOOK_PAGE_ID = os.environ["FACEBOOK_PAGE_ID"]
FACEBOOK_PAGE_ACCESS_TOKEN = os.environ["FACEBOOK_PAGE_ACCESS_TOKEN"]

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
    #refresh_token=REFRESH_TOKEN,
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
# AI CONTEXTUAL HASHTAG ENGINE
# ==============================

def generate_contextual_tags(video_name):

    name = video_name.lower()

    topic_map = {
        "karma": ["karma", "karmayoga", "duty"],
        "anger": ["anger", "selfcontrol", "innerpeace"],
        "mind": ["mind", "focus", "clarity"],
        "fear": ["fearless", "confidence", "courage"],
        "success": ["success", "discipline", "growth"],
        "attachment": ["detachment", "vairagya"],
        "death": ["soul", "atman", "rebirth"],
        "love": ["divinelove", "radhakrishna"],
        "stress": ["stressrelief", "calm"],
        "motivation": ["motivation", "lifelessons"]
    }

    contextual = []

    for key in topic_map:
        if key in name:
            contextual += topic_map[key]

    if not contextual:
        contextual = ["wisdom", "spiritualgrowth", "krishnawords"]

    return contextual

# ==============================
# BEST PERFORMING HOOK DETECTOR
# ==============================

def get_best_performing_hook():

    if not os.path.exists("performance_log.csv"):
        return None

    hook_views = {}

    with open("performance_log.csv", "r") as log:
        lines = log.readlines()

    for line in lines:
        parts = line.strip().split(",")

        if len(parts) < 3:
            continue

        hook = parts[1]

        if hook not in hook_views:
            hook_views[hook] = 0

        hook_views[hook] += 1   # Count usage frequency only

    if not hook_views:
        return None

    best_hook = max(hook_views, key=hook_views.get)

    print(f"🏆 Most Used Hook So Far: {best_hook}")

    return best_hook

# ==============================
# TITLE + TAG SYSTEM
# ==============================

title_hooks = [
    "Stop Scrolling – Krishna Is Speaking To You",
    "This Krishna Message Will Change Your Life",
    "One Gita Line That Hits Different",
    "Your Sign from the Bhagavad Gita Today",
    "Krishna’s Powerful Advice for Tough Times",
    "Read This Before You Sleep",
    "Life Changing Gita Wisdom",
    "This Verse Feels Personal",
    "Deep Spiritual Truth of Life",
    "Krishna’s Secret for Inner Peace"
]

evergreen_tags = [
    "bhagavadgita", "krishna", "radhakrishna",
    "bhakti", "devotional", "spirituality",
    "sanatandharma", "hinduism"
]

viral_tags = [
    "shorts", "youtubeshorts", "viralshorts",
    "reels", "explorepage", "trending",
    "reelsindia", "shortsvideo"
]

emotion_tags = [
    "motivation", "lifequotes", "wisdom",
    "mindset", "selfgrowth", "positivevibes"
]

hindi_tags = [
    "geeta", "krishnabhakti",
    "bhaktistatus", "sanatan",
    "hindudharma", "hindiquotes"
]

today = datetime.now().strftime("%A").lower()

weekday_special = {
    "monday": "shivbhakti",
    "tuesday": "hanuman",
    "wednesday": "krishnalove",
    "thursday": "guruvaar",
    "friday": "laxmimata",
    "saturday": "shanidev",
    "sunday": "spiritualsunday"
}

special_day_tag = weekday_special.get(today, "")

# ==============================
# FETCH VIDEOS FROM DRIVE
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

videos_to_process = files[:4]
print(f"Found {len(videos_to_process)} video(s)")

# ==============================
# PROCESS EACH VIDEO
# ==============================

for video in videos_to_process:

    print("\n==============================")
    print("Processing:", video["name"])

    request = drive_service.files().get_media(fileId=video["id"])
    fh = io.FileIO(video["name"], "wb")
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    # SMART TITLE SELECTION

    best_hook = get_best_performing_hook()

    if best_hook and random.random() < 0.7:
        chosen_hook = best_hook
    else:
        chosen_hook = random.choice(title_hooks)

    title = f"{chosen_hook} | Episode {episode_number}"

    # SMART TAGS

    context_tags = generate_contextual_tags(video["name"])

    selected_tags = list(set(
        random.sample(evergreen_tags, 3) +
        random.sample(viral_tags, 3) +
        random.sample(emotion_tags, 3) +
        random.sample(hindi_tags, 2) +
        random.sample(context_tags, min(3, len(context_tags))) +
        ([special_day_tag] if special_day_tag else [])
    ))

    hashtags = " ".join([f"#{tag}" for tag in selected_tags])

    description = f"""
Daily Krishna Wisdom 🙏

Ancient knowledge for modern success.

{hashtags}
"""

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
                    "tags": selected_tags,
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

        print("✅ YouTube Uploaded:", video_id)

        used_hook = chosen_hook

        with open("performance_log.csv", "a") as log:
            log.write(f"{video_id},{used_hook},{title},{datetime.now()}\n")

    except Exception as e:
        print("❌ YouTube Upload Failed:", str(e))
        os.remove(video["name"])
        continue

    # ==============================
    # UPLOAD TO FACEBOOK
    # ==============================

    # ==============================
# FACEBOOK REELS UPLOAD (CORRECT)
# ==============================

try:
    file_path = video["name"]
    file_size = os.path.getsize(file_path)

    # STEP 1 — START
    start_url = f"https://graph.facebook.com/v24.0/{FACEBOOK_PAGE_ID}/video_reels"

    start_response = requests.post(
        start_url,
        data={
            "upload_phase": "start",
            "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
        }
    ).json()

    if "error" in start_response:
        raise Exception(start_response)

    video_id = start_response["video_id"]
    upload_url = start_response["upload_url"]

    print("📤 Upload session started:", video_id)

    # STEP 2 — TRANSFER
    with open(file_path, "rb") as f:
        transfer_response = requests.post(
            upload_url,
            headers={
                "Authorization": f"OAuth {FACEBOOK_PAGE_ACCESS_TOKEN}",
                "offset": "0"
            },
            data=f
        ).json()

    if "error" in transfer_response:
        raise Exception(transfer_response)

    print("📦 Video transferred")

    # STEP 3 — FINISH
    finish_response = requests.post(
        start_url,
        data={
            "upload_phase": "finish",
            "video_id": video_id,
            "description": description,
            "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
        }
    ).json()

    if "error" in finish_response:
        raise Exception(finish_response)

    print("✅ Facebook Reel Uploaded:", video_id)

except Exception as e:
    print("❌ Facebook Upload Failed:", e)

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

print("\n🎉 All uploads completed successfully.")
