import os
import io
import json
from datetime import datetime, timedelta, timezone
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2.credentials import Credentials

FOLDER_ID = os.environ["FOLDER_ID"]
UPLOADED_FOLDER_ID = os.environ["UPLOADED_FOLDER_ID"]
REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]

# ---- EXACT PUBLISH TIME FUNCTION
def get_exact_publish_time():
    now_utc = datetime.now(timezone.utc)
    ist_now = now_utc + timedelta(hours=5, minutes=30)

    # Morning run
    if ist_now.hour < 12:
        target_ist = ist_now.replace(hour=8, minute=0, second=0, microsecond=0)
    else:
        target_ist = ist_now.replace(hour=17, minute=0, second=0, microsecond=0)

    target_utc = target_ist - timedelta(hours=5, minutes=30)
    return target_utc.isoformat().replace("+00:00", "Z")

# ---- DRIVE AUTH
service_account_info = json.loads(os.environ["SERVICE_ACCOUNT_JSON"])
drive_creds = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/drive"]
)
drive_service = build("drive", "v3", credentials=drive_creds)

# ---- YOUTUBE AUTH
youtube_creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["https://www.googleapis.com/auth/youtube.upload"]
)
youtube = build("youtube", "v3", credentials=youtube_creds)

# ---- READ EPISODE NUMBER
if os.path.exists("episode.txt"):
    with open("episode.txt", "r") as f:
        episode_number = int(f.read().strip())
else:
    episode_number = 1

# ---- GET VIDEOS
results = drive_service.files().list(
    q=f"'{FOLDER_ID}' in parents and mimeType contains 'video/'",
    orderBy="createdTime asc",
    fields="files(id, name)"
).execute()

files = results.get("files", [])

if not files:
    print("No videos found.")
    exit()

# Upload MAX 2 videos per run
videos_to_upload = files[:2]

publish_time = get_exact_publish_time()

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
    print("Scheduled:", response["id"])

    drive_service.files().update(
        fileId=file["id"],
        addParents=UPLOADED_FOLDER_ID,
        removeParents=FOLDER_ID
    ).execute()

    os.remove(file["name"])
    episode_number += 1

with open("episode.txt", "w") as f:
    f.write(str(episode_number))

print("Episode number updated successfully.")
