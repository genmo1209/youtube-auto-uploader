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
SOURCE_FOLDER_ID = os.getenv("UPLOADED_FOLDER_ID_CH3")  # Drive source folder
DEST_FOLDER_ID = os.getenv("Uploaded_FB_Pyscho")        # Drive uploaded folder
LOG_FILE = "Uploaded_FB_Pyscho.json"
SERVICE_ACCOUNT_JSON_CONTENT = os.getenv("SERVICE_ACCOUNT_JSON")

# -------------------------------
# HOOK GENERATOR BASE
# -------------------------------
PSYCHO_TOPICS = [
    "lying", "attraction", "fear", "confidence", "procrastination",
    "overthinking", "body language", "memory", "trauma",
    "happiness", "subconscious mind", "decision making"
]

HOOK_TEMPLATES = [
    "Your brain does THIS when it comes to {topic} 😳",
    "The hidden psychology behind {topic} 🤯",
    "Why you secretly struggle with {topic} 😶",
    "The science of {topic} explained in 30 seconds 🧠",
    "This truth about {topic} will shock you 😱",
    "What nobody tells you about {topic} 👀",
]

HASHTAGS_POOL = [
    "#Psychology", "#MindHacks", "#BrainFacts", "#MentalHealth",
    "#SelfImprovement", "#HumanBehavior", "#Neuroscience",
    "#DailyPsychology", "#Mindset", "#Confidence",
    "#Overthinking", "#LifeHacks", "#Reels", "#ViralReels",
    "#InstagramReels", "#FacebookReels"
]

# -------------------------------
# Generate Title + Hashtags
# -------------------------------
def generate_caption():
    topic = random.choice(PSYCHO_TOPICS)
    template = random.choice(HOOK_TEMPLATES)
    title = template.format(topic=topic)

    hashtags = " ".join(random.sample(HASHTAGS_POOL, 8))

    return title, hashtags

# -------------------------------
# Write Service Account JSON
# -------------------------------
with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
    temp_file.write(SERVICE_ACCOUNT_JSON_CONTENT.encode())
    SERVICE_ACCOUNT_JSON_PATH = temp_file.name

# -------------------------------
# Authenticate Drive
# -------------------------------
SCOPES = ["https://www.googleapis.com/auth/drive"]
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_JSON_PATH, scopes=SCOPES
)
drive_service = build('drive', 'v3', credentials=credentials)

# -------------------------------
# Load Uploaded Log
# -------------------------------
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r") as f:
        uploaded_videos = json.load(f)
else:
    uploaded_videos = []

# -------------------------------
# Get Files From Drive
# -------------------------------
results = drive_service.files().list(
    q=f"'{SOURCE_FOLDER_ID}' in parents and trashed=false",
    fields="files(id, name)"
).execute()

files = results.get("files", [])

if not files:
    print("No files found.")
    exit()

# -------------------------------
# Move File After Upload
# -------------------------------
def move_file(file_id):
    file = drive_service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents', []))
    drive_service.files().update(
        fileId=file_id,
        addParents=DEST_FOLDER_ID,
        removeParents=previous_parents
    ).execute()

# -------------------------------
# Upload Only ONE Video as Draft
# -------------------------------
uploaded_this_run = False

for file in files:

    if uploaded_this_run:
        break

    if file["id"] in uploaded_videos:
        continue

    print(f"Uploading: {file['name']}")

    download_url = f"https://www.googleapis.com/drive/v3/files/{file['id']}?alt=media"

    title, hashtags = generate_caption()

    upload_url = f"https://graph.facebook.com/v25.0/{FB_PAGE_ID}/videos"

    payload = {
        "title": title,
        "description": f"{title}\n\n{hashtags}",
        "file_url": download_url,
        "published": "false",  # IMPORTANT: Draft mode
        "access_token": FB_PAGE_TOKEN
    }

    response = requests.post(upload_url, data=payload)
    result = response.json()

    if "id" in result:
        print("Uploaded as draft successfully.")
        uploaded_videos.append(file["id"])
        move_file(file["id"])
        uploaded_this_run = True
    else:
        print("Upload failed:", result)

# -------------------------------
# Save Log
# -------------------------------
with open(LOG_FILE, "w") as f:
    json.dump(uploaded_videos, f, indent=2)

print("Done. Only 1 draft uploaded.")
