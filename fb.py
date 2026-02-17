import os
import io
import json
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ==============================
# ENV VARIABLES
# ==============================

FOLDER_ID = os.environ["FOLDER_ID"]
UPLOADED_FOLDER_ID = os.environ["UPLOADED_FOLDER_ID"]
FACEBOOK_PAGE_ID = os.environ["FACEBOOK_PAGE_ID"]
FACEBOOK_PAGE_ACCESS_TOKEN = os.environ["FACEBOOK_PAGE_ACCESS_TOKEN"]

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
# GET VIDEO FROM DRIVE
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

video = files[0]
print("Processing:", video["name"])

# ==============================
# DOWNLOAD VIDEO
# ==============================

request = drive_service.files().get_media(fileId=video["id"])
fh = io.FileIO(video["name"], "wb")
downloader = MediaIoBaseDownload(fh, request)

done = False
while not done:
    status, done = downloader.next_chunk()

title = "Bhagavad Gita Daily Dose"
description = """Bhagavad Gita Daily Dose – Verse of the Day

#bhakti #devotional #spiritual #krishna
"""

# ==============================
# UPLOAD TO FACEBOOK
# ==============================

url = f"https://graph.facebook.com/v24.0/{FACEBOOK_PAGE_ID}/videos"

with open(video["name"], "rb") as video_file:
    files_data = {"source": video_file}
    data = {
        "title": title,
        "description": description,
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
    }
    response = requests.post(url, files=files_data, data=data)

print("Facebook Response:", response.json())

# ==============================
# MOVE FILE
# ==============================

drive_service.files().update(
    fileId=video["id"],
    addParents=UPLOADED_FOLDER_ID,
    removeParents=FOLDER_ID
).execute()

os.remove(video["name"])

print("Facebook upload completed successfully.")