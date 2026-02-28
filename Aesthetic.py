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
# ENV VARIABLES (CHANNEL 3)
# ==============================

FOLDER_ID = os.environ["FOLDER_ID_CH3"]
UPLOADED_FOLDER_ID = os.environ["UPLOADED_FOLDER_ID_CH3"]

YT_CLIENT_ID = os.environ["YT_CLIENT_ID_CH3"]
YT_CLIENT_SECRET = os.environ["YT_CLIENT_SECRET_CH3"]
YT_REFRESH_TOKEN = os.environ["YT_REFRESH_TOKEN_CH3"]

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
# EXPLOSIVE PSYCHOLOGY ENGINE
# ==============================

power_words = [
    "Brutal Truth About",
    "Harsh Reality Of",
    "Psychology Behind",
    "Scientifically Proven",
    "The Dark Side Of"
]

emojis = ["🧠", "⚡", "🔍", "💭", "🔥", "📌"]

# Emotional Intensity Scale (1–10)
emotional_intensity_map = {
    "Manipulation": 10,
    "Self-Sabotage": 10,
    "Toxic Behavior": 10,
    "Emotional Trauma": 10,
    "Rejection": 10,
    "Loneliness": 9,
    "Attachment": 9,
    "Overthinking": 8,
    "Love": 7,
    "Confidence": 6,
    "Human Nature": 6,
    "Emotional Intelligence": 5
}

curiosity_words = ["Truth", "Reality", "Dark", "Secret", "Hidden", "Why"]

def calculate_emotional_intensity(title):
    for topic, value in emotional_intensity_map.items():
        if topic in title:
            return value
    return 0


def score_title(title):
    score = 0

    # Structure bonus
    if any(word in title for word in power_words):
        score += 2

    # Curiosity bonus
    if any(word in title for word in curiosity_words):
        score += 2

    # Emoji bonus
    if any(e in title for e in emojis):
        score += 1

    # Length optimization (Shorts sweet spot)
    if 40 <= len(title) <= 65:
        score += 2

    # Emotional intensity weight
    intensity = calculate_emotional_intensity(title)
    score += intensity * 0.8

    return round(score, 2), intensity


def generate_best_title():
    print("\n🔥 Explosive Mode Activated (Intensity 9–10 Only)")

    while True:
        candidates = []

        for _ in range(15):
            phrase = random.choice(power_words)
            topic = random.choice(list(emotional_intensity_map.keys()))
            emoji = random.choice(emojis)
            title = f"{phrase} {topic} {emoji} #Shorts"
            candidates.append(title)

        scored_titles = []

        for title in candidates:
            total_score, intensity = score_title(title)
            scored_titles.append((title, total_score, intensity))

        explosive_titles = [t for t in scored_titles if t[2] >= 9]

        if explosive_titles:
            explosive_titles.sort(key=lambda x: x[1], reverse=True)

            print("\n💥 Explosive Candidates:")
            for t, s, i in explosive_titles:
                print(f"Score: {s} | Intensity: {i}/10 → {t}")

            best_title = explosive_titles[0][0]
            best_score = explosive_titles[0][1]
            best_intensity = explosive_titles[0][2]

            print("\n🏆 SELECTED EXPLOSIVE TITLE")
            print(f"{best_title}")
            print(f"🔥 Score: {best_score}")
            print(f"💣 Emotional Intensity: {best_intensity}/10")

            return best_title

        print("⚠ No 9+ intensity title found. Regenerating...")

# ==============================
# HASHTAG ENGINE
# ==============================

hashtag_groups = [
    ["psychology", "darkpsychology", "humanbehavior", "selfawareness"],
    ["mentalhealth", "overthinking", "emotions", "relationships"],
    ["mindset", "attachment", "toxic", "selfgrowth"]
]

shorts_boost_tags = ["shorts", "ytshorts", "viralshorts"]

def generate_hashtags():
    group = random.choice(hashtag_groups)
    return list(set(group + shorts_boost_tags))

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

print(f"\n🚀 Preparing to upload {len(videos_to_process)} video(s)...")

# ==============================
# PROCESS & UPLOAD
# ==============================

for video in videos_to_process:

    print("\n================================")

    video_id = video.get("id")
    video_name = video.get("name")

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

        # TITLE + TAGS
        title = generate_best_title()
        hashtags = generate_hashtags()

        description_base = """
🧠 Psychological Talks – Understand People. Understand Yourself.

Deep psychological insights that reveal hidden human behavior.

Comment "MIND" if this hits you.
"""

        description = f"{description_base}\n\n" + " ".join(
            [f"#{tag}" for tag in hashtags]
        )

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

        print("✅ Uploaded:", response.get("id"))

        # MOVE FILE
        drive_service.files().update(
            fileId=video_id,
            addParents=UPLOADED_FOLDER_ID,
            removeParents=FOLDER_ID
        ).execute()

        os.remove(video_name)

        gap = random.randint(5, 12)
        print(f"⏱ Sleeping {gap}s...")
        time.sleep(gap)

    except Exception as e:
        print("❌ Error:", str(e))
        traceback.print_exc()

        if os.path.exists(video_name):
            os.remove(video_name)

        continue

print("\n🎉 All uploads completed successfully!")
