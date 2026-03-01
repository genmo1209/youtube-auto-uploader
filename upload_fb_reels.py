import os
import json
import requests
import tempfile
import random
from google.oauth2 import service_account
from googleapiclient.discovery import build

# -------------------------------
# CONFIGURATION
# -------------------------------
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN")
GDRIVE_FOLDER_ID = os.getenv("UPLOADED_FOLDER_ID_CH3")  # Source folder secret
UPLOADED_FOLDER_ID = os.getenv("Uploaded_FB_Pyscho")    # Destination folder secret
LOG_FILE = "Uploaded_FB_Pyscho.json"
SERVICE_ACCOUNT_JSON_CONTENT = os.getenv("SERVICE_ACCOUNT_JSON")

# -------------------------------
# Hooks and Hashtags for titles
# -------------------------------
HOOKS = [
    "Your brain does THIS when you lie 😳",
    "Why you always remember embarrassing moments 🤯",
    "The psychology trick marketers don’t want you to know 🧠",
    "This one habit rewires your brain in 30 days ✨",
    "Why people fall for the same mistake repeatedly 😱",
    "The hidden reason you can’t resist scrolling Instagram 📱",
    "Your subconscious is controlling you… here’s how",
    "Why happy people are secretly sad 😔",
    "The shocking effect of color on your mind 🎨",
    "This everyday decision reveals your true personality 😲",
    "How your brain reacts to compliments 😎",
    "The real reason you procrastinate ⏳",
    "Your mind has secrets even you don’t know 🤯",
    "Why fear feels so real even when there’s no danger 😱",
    "The science of instant attraction ❤️",
    "This tiny habit can change your life in 7 days 🧠",
    "Why we remember trauma more than happiness 😔",
    "How your decisions are predicted by your subconscious 🤯",
    "The hidden power of your imagination 🌌",
    "This one trick boosts your confidence instantly 💪"
]

HASHTAGS = [
    "#Psychology", "#BrainFacts", "#MindHacks", "#MentalHealth", "#PsychologyFacts",
    "#SelfAwareness", "#HumanMind", "#Neuroscience", "#Behavior", "#LifeHacks",
    "#MindTricks", "#FacelessReels", "#ViralReels", "#Shorts", "#LearnOnReels",
    "#DailyPsychology", "#Motivation", "#SelfImprovement", "#MentalTips", "#MindPower"
]

# -------------------------------
# Write service account JSON to temp file
# -------------------------------
with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
    temp_file.write(SERVICE_ACCOUNT_JSON_CONTENT.encode())
    SERVICE_ACCOUNT_JSON_PATH = temp_file.name

# -------------------------------
# Authenticate to Google Drive
# -------------------------------
SCOPES = ["https://www.googleapis.com/auth/drive"]
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_JSON_PATH, scopes=SCOPES
)
drive_service = build('drive', 'v3', credentials=credentials)

# -------------------------------
# Load previously uploaded videos
# -------------------------------
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r") as f:
        uploaded_videos = json.load(f)
else:
    uploaded_videos = []

# -------------------------------
# List files in source folder
# -------------------------------
results = drive_service.files().list(
    q=f"'{GDRIVE_FOLDER_ID}' in parents and trashed=false",
    fields="files(id, name, mimeType)"
).execute()
files = results.get("files", [])

# -------------------------------
# Function to move uploaded files
# -------------------------------
def move_file(file_id):
    file = drive_service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents', []))
    drive_service.files().update(
        fileId=file_id,
        addParents=UPLOADED_FOLDER_ID,
        removeParents=previous_parents,
        fields='id, parents'
    ).execute()
    print(f"Moved file {file_id} to Uploaded_FB_Pyscho folder.")

# -------------------------------
# Upload each video
# -------------------------------
for file in files:
    if file["id"] in uploaded_videos:
        print(f"Skipping already uploaded: {file['name']}")
        continue

    print(f"Uploading: {file['name']}")
    download_url = f"https://www.googleapis.com/drive/v3/files/{file['id']}?alt=media"

    # Pick a random hook and hashtags
    hook = random.choice(HOOKS)
    hashtags = " ".join(random.sample(HASHTAGS, k=10))

    upload_url = f"https://graph.facebook.com/v25.0/{FB_PAGE_ID}/videos"
    payload = {
        "title": hook,
        "description": f"{hook} {hashtags}",
        "file_url": download_url,
        "published": "false",
        "access_token": FB_PAGE_TOKEN
    }

    response = requests.post(upload_url, data=payload)
    result = response.json()

    if "id" in result:
        video_id = result["id"]
        print(f"Uploaded successfully, video ID: {video_id}")
        uploaded_videos.append(file["id"])
        move_file(file["id"])  # Move to Uploaded_FB_Pyscho
    else:
        print(f"Failed to upload: {result}")

# -------------------------------
# Save log of uploaded videos
# -------------------------------
with open(LOG_FILE, "w") as f:
    json.dump(uploaded_videos, f, indent=2)

print("All done!")
