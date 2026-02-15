import os
import io
import json
import requests
from datetime import datetime, timedelta, timezone
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2.credentials import Credentials

# ==============================
# ENV VARIABLES
# ==============================

FOLDER_ID = os.environ["FOLDER_ID"]
UPLOADED_FOLDER_ID = os.environ["UPLOADED_FOLDER_ID"]
REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]

# ✅ NEW FACEBOOK VARIABLES
FACEBOOK_PAGE_ID = os.environ["FACEBOOK_PAGE_ID"]
FACEBOOK_PAGE_ACCESS_TOKEN = os.environ["FACEBOOK_PAGE_ACCESS_TOKEN"]


# ==============================
# EXACT PUBLISH TIME FUNCTION
# ==============================

def get_exact_publish_time():
    now_utc = datetime.now(timezone.utc)
    ist_now = now_utc + timedelta(hours=5, minutes=30)

    if ist_now.hour < 12:
        target_ist = ist_now.replace(hour=8, minute=0, second=0, microsecond=0)
    else:
        target_ist = ist_now.replace(hour=17, minute=0, second=0, microsecond=0)

    target_utc = target_ist - timedelta(hours=5, minutes=30)
    return target_utc.isoformat().replace("+00:00", "Z")


# ==============================
# FACEBOOK UPLOAD FUNCTION
# ==============================

def upload_to_facebook(video_path, title, description):
    print("Uploading to Facebook...")

    url = f"https://graph.facebook.com/v24.0/{FACEBOOK_PAGE_ID}/videos"

    with open(video_path, "rb") as video_file:
        files = {
            "source": video_file
        }

        data = {
            "title": title,
            "description": description,
            "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
        }

        response = requests.post(url, files=files, data=data)

    print("Facebook Response:", response.json())


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
# YOUTUBE AUTH
# ==============================

youtube_creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["https://www.googleapis.com/auth/youtube.upload"]
)
youtube = build("youtube", "v3", credentials=youtube_creds)


# ==============================
# READ EPISODE NUMBER
# ==============================

if os.path.exists("episode.txt"):
    with open("episode.txt", "r") as f:
        episode_number = int(f.read().strip())
else:
    episode_number = 1


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

videos_to_upload = files[:2]
publish_time = get_exact_publish_time()


# ==============================
# MAIN LOOP
# ==============================

for file in videos_to_upload:
    print("Processing:", file["name"])

    request = drive_service.files().get_media(fileId=file["id"])
    fh = io.FileIO(file["name"], "wb")
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    title = f"Bhagavad Gita Daily Dose – Verse of the Day | Episode {episode_number}"

    description = """Bhagavad Gita Daily Dose – Verse of the Day

#bhakti #devotional #spiritual #faith #god #krishna
#radhakrishna #mahadev #shiva #hanuman #bholenath
#bhajan #harekrishna #sanatandharma #shorts
"""

    # ==============================
    # YOUTUBE UPLOAD
    # ==============================

    media = MediaFileUpload(file["name"], resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": ["bhakti", "devotional", "gita", "krishna", "shorts"],
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": "private",
                "publishAt": publish_time
            }
        },
        media_body=media
    )

    response = request.execute()
    print("YouTube Scheduled:", response["id"])

    # ==============================
    # FACEBOOK UPLOAD
    # ==============================

    upload_to_facebook(file["name"], title, description)

    # ==============================
    # MOVE FILE IN DRIVE
    # ==============================

    drive_service.files().update(
        fileId=file["id"],
        addParents=UPLOADED_FOLDER_ID,
        removeParents=FOLDER_ID
    ).execute()

    os.remove(file["name"])
    episode_number += 1


# ==============================
# UPDATE EPISODE NUMBER
# ==============================

with open("episode.txt", "w") as f:
    f.write(str(episode_number))

print("Episode number updated successfully.")
