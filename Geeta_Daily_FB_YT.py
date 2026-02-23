import os
import re
import random
from collections import defaultdict

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==========================================
# ENV VARIABLES (SET IN GITHUB SECRETS)
# ==========================================

CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]

VIDEO_FOLDER = "videos"   # Folder containing shorts
MAX_RESULTS = 50          # Fetch last 50 videos for analysis

# ==========================================
# AUTHENTICATION (REFRESH TOKEN BASED)
# ==========================================

creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["https://www.googleapis.com/auth/youtube"]
)

youtube = build("youtube", "v3", credentials=creds)

# ==========================================
# FETCH RECENT VIDEOS
# ==========================================

def get_recent_videos():
    print("📊 Fetching recent videos for hook optimization...")

    request = youtube.search().list(
        part="id",
        forMine=True,
        type="video",
        order="date",
        maxResults=MAX_RESULTS
    )
    response = request.execute()

    video_ids = [item["id"]["videoId"] for item in response["items"]]

    if not video_ids:
        return []

    stats_request = youtube.videos().list(
        part="statistics,snippet",
        id=",".join(video_ids)
    )
    stats_response = stats_request.execute()

    videos = []

    for item in stats_response["items"]:
        title = item["snippet"]["title"]
        views = int(item["statistics"].get("viewCount", 0))

        videos.append({
            "title": title,
            "views": views
        })

    return videos

# ==========================================
# HOOK EXTRACTION
# ==========================================

def extract_hook(title):
    words = title.split()
    return " ".join(words[:4]).strip()

def get_best_hook(videos):
    hook_views = defaultdict(int)
    hook_count = defaultdict(int)

    for video in videos:
        hook = extract_hook(video["title"])
        hook_views[hook] += video["views"]
        hook_count[hook] += 1

    if not hook_views:
        return None

    hook_score = {
        hook: hook_views[hook] / hook_count[hook]
        for hook in hook_views
    }

    best_hook = max(hook_score, key=hook_score.get)
    print(f"🏆 Best Performing Hook: {best_hook}")
    return best_hook

# ==========================================
# GENERATE TITLE
# ==========================================

def generate_title(best_hook):
    fallback_hooks = [
        "Why Krishna Said This",
        "Krishna Warned About This",
        "Stop Doing This Today",
        "This One Line Will Change You"
    ]

    if not best_hook:
        best_hook = random.choice(fallback_hooks)

    episode_number = random.randint(1, 999)

    return f"{best_hook} | Bhagavad Gita Short #{episode_number} #shorts"

# ==========================================
# UPLOAD VIDEO
# ==========================================

def upload_video(file_path, title):
    print(f"🚀 Uploading: {file_path}")

    body = {
        "snippet": {
            "title": title,
            "description": "Daily Bhagavad Gita wisdom 🙏 #shorts",
            "tags": ["Bhagavad Gita", "Krishna", "Spiritual", "Motivation"],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public"
        }
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()

    print(f"✅ Uploaded: {response['id']}")

# ==========================================
# MAIN PROCESS
# ==========================================

def main():
    videos = get_recent_videos()
    best_hook = get_best_hook(videos)

    for file in os.listdir(VIDEO_FOLDER):
        if file.endswith(".mp4"):
            file_path = os.path.join(VIDEO_FOLDER, file)

            title = generate_title(best_hook)
            upload_video(file_path, title)

            # Upload one video per run
            break


if __name__ == "__main__":
    main()
