import os
import requests
import time
import hashlib
import random
from pytrends.request import TrendReq

# ==============================
# ENV VARIABLES
# ==============================

ACCESS_TOKEN = os.environ["PYSCHO_ACCESS_TOKEN"]
FB_PAGE_ID = os.environ["PYSCHO_FB_PAGE_ID"]
IG_BUSINESS_ID = os.environ["PYSCHO_IG_BUSINESS_ID"]

CLOUD_NAME = os.environ["PYSCHO_CLOUDINARY_CLOUD_NAME"]
API_KEY = os.environ["PYSCHO_CLOUDINARY_API_KEY"]
API_SECRET = os.environ["PYSCHO_CLOUDINARY_API_SECRET"]

GRAPH_URL = "https://graph.facebook.com/v25.0"

# ==============================
# TRENDING CAPTION SYSTEM
# ==============================

HOOK_TEMPLATES = [
    "The hidden psychology behind {topic} 🤯",
    "Nobody talks about this truth about {topic} 😳",
    "Why your brain reacts like this to {topic} 🧠",
    "The science behind {topic} explained simply",
    "This is why {topic} controls your life 😱",
]

BASE_HASHTAGS = [
    "#Psychology",
    "#Mindset",
    "#SelfGrowth",
    "#MentalHealth",
    "#HumanBehavior",
    "#ReelsIndia",
]

def generate_trending_caption():
    try:
        pytrends = TrendReq(hl='en-US', tz=330, timeout=(10, 25))
        trends = pytrends.trending_searches(pn='india')[0].tolist()

        topic = random.choice(trends[:10])
        hook = random.choice(HOOK_TEMPLATES).format(topic=topic)

        trend_tags = [
            f"#{t.replace(' ', '')}" for t in random.sample(trends[:10], 3)
        ]

        base_tags = random.sample(BASE_HASHTAGS, 3)

        return hook + "\n\n" + " ".join(trend_tags + base_tags)

    except Exception as e:
        print(f"Trends fetch failed: {e}")
        return (
            "The hidden psychology behind overthinking 🤯\n\n"
            "#Psychology #Mindset #ReelsIndia"
        )

# ==============================
# GET VIDEO FROM CLOUDINARY
# ==============================

def get_pending_video():
    url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/resources/video"

    response = requests.get(
        url,
        auth=(API_KEY, API_SECRET),
        params={"type": "upload", "max_results": 1, "prefix": "pending/"}
    )

    data = response.json()
    print("Cloudinary Response:", data)

    if "resources" not in data or len(data["resources"]) == 0:
        # Fallback: fetch from root if no pending/ folder
        response = requests.get(
            url,
            auth=(API_KEY, API_SECRET),
            params={"type": "upload", "max_results": 1}
        )
        data = response.json()
        print("Cloudinary Fallback Response:", data)

    if "resources" not in data or len(data["resources"]) == 0:
        print("No videos found.")
        return None, None

    video = data["resources"][0]
    return video["secure_url"], video["public_id"]

# ==============================
# MOVE FILE (Cloudinary)
# ==============================

def move_asset(public_id, folder):
    timestamp = int(time.time())
    new_public_id = f"{folder}/{public_id.split('/')[-1]}"

    string_to_sign = (
        f"from_public_id={public_id}&"
        f"timestamp={timestamp}&"
        f"to_public_id={new_public_id}"
    )

    signature = hashlib.sha1(
        (string_to_sign + API_SECRET).encode()
    ).hexdigest()

    url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/video/rename"

    response = requests.post(
        url,
        data={
            "from_public_id": public_id,
            "to_public_id": new_public_id,
            "api_key": API_KEY,
            "timestamp": timestamp,
            "signature": signature,
        }
    )

    print("Move Response:", response.json())

# ==============================
# FACEBOOK REELS (FIXED)
# ==============================

def post_facebook(video_url, caption):
    print("Uploading Facebook Reel...")

    # STEP 1: START
    start_res = requests.post(
        f"{GRAPH_URL}/{FB_PAGE_ID}/video_reels",
        data={
            "upload_phase": "start",
            "access_token": ACCESS_TOKEN
        }
    ).json()

    print("Start Response:", start_res)

    if "upload_url" not in start_res:
        print("❌ Failed to start upload:", start_res)
        return False

    upload_url = start_res["upload_url"]
    video_id = start_res["video_id"]

    # Download video binary
    print("Downloading video from Cloudinary...")
    video_binary = requests.get(video_url).content
    file_size = len(video_binary)
    print(f"Video size: {file_size} bytes")

    # STEP 2: TRANSFER
    print("Transferring video to Facebook...")
    transfer_res = requests.post(
        upload_url,
        headers={
            "Authorization": f"OAuth {ACCESS_TOKEN}",
            "offset": "0",
            "file_size": str(file_size),
            "Content-Type": "application/octet-stream"
        },
        data=video_binary
    ).json()

    print("Transfer Response:", transfer_res)

    if "success" not in transfer_res:
        print("❌ Video transfer failed")
        return False

    # STEP 3: FINISH
    print("Publishing Facebook Reel...")
    finish_res = requests.post(
        f"{GRAPH_URL}/{FB_PAGE_ID}/video_reels",
        data={
            "upload_phase": "finish",
            "video_id": video_id,
            "description": caption,
            "video_state": "PUBLISHED",
            "access_token": ACCESS_TOKEN
        }
    ).json()

    print("Finish Response:", finish_res)

    if "error" in finish_res:
        print("❌ Facebook publish failed:", finish_res)
        return False

    print("✅ Facebook Reel Uploaded Successfully")
    return True

# ==============================
# INSTAGRAM REELS
# ==============================

def post_instagram(video_url, caption):
    print("Uploading Instagram Reel...")

    # STEP 1: Create container
    container = requests.post(
        f"{GRAPH_URL}/{IG_BUSINESS_ID}/media",
        data={
            "video_url": video_url,
            "caption": caption,
            "media_type": "REELS",
            "access_token": ACCESS_TOKEN
        }
    ).json()

    print("IG Container:", container)

    if "id" not in container:
        print("❌ IG container failed:", container)
        return False

    creation_id = container["id"]

    # STEP 2: Wait for processing
    print("Waiting for Instagram to process video...")
    for attempt in range(30):
        time.sleep(5)

        status = requests.get(
            f"{GRAPH_URL}/{creation_id}",
            params={
                "fields": "status_code",
                "access_token": ACCESS_TOKEN
            }
        ).json()

        print(f"IG Status [{attempt + 1}/30]:", status)

        if status.get("status_code") == "FINISHED":
            break
        elif status.get("status_code") == "ERROR":
            print("❌ IG processing error")
            return False
    else:
        print("❌ IG processing timeout")
        return False

    # STEP 3: Publish
    print("Publishing Instagram Reel...")
    publish = requests.post(
        f"{GRAPH_URL}/{IG_BUSINESS_ID}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": ACCESS_TOKEN
        }
    ).json()

    print("IG Publish:", publish)

    if "error" in publish:
        print("❌ IG publish failed:", publish)
        return False

    print("✅ Instagram Reel Uploaded Successfully")
    return True

# ==============================
# MAIN
# ==============================

def main():
    video_url, public_id = get_pending_video()

    if not video_url:
        print("No video to process. Exiting.")
        return

    caption = generate_trending_caption()
    print("Caption:", caption)

    # Small delay between platforms
    fb_success = post_facebook(video_url, caption)
    time.sleep(5)
    ig_success = post_instagram(video_url, caption)

    if fb_success and ig_success:
        move_asset(public_id, "uploaded")
        print("✅ Both platforms succeeded → moved to uploaded/")
    elif fb_success:
        move_asset(public_id, "uploaded_fb_only")
        print("⚠️ Only Facebook succeeded → moved to uploaded_fb_only/")
    elif ig_success:
        move_asset(public_id, "uploaded_ig_only")
        print("⚠️ Only Instagram succeeded → moved to uploaded_ig_only/")
    else:
        move_asset(public_id, "failed")
        print("❌ Both platforms failed → moved to failed/")

if __name__ == "__main__":
    main()
