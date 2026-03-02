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

GRAPH_URL = "https://graph.facebook.com/v24.0"

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
        pytrends = TrendReq(hl='en-IN', tz=330)
        trends = pytrends.trending_searches(pn='india')[0].tolist()

        topic = random.choice(trends[:15])
        hook = random.choice(HOOK_TEMPLATES).format(topic=topic)

        trend_tags = [
            f"#{t.replace(' ', '')}" for t in random.sample(trends[:15], 3)
        ]

        base_tags = random.sample(BASE_HASHTAGS, 3)

        hashtags = " ".join(trend_tags + base_tags)

        return hook + "\n\n" + hashtags

    except Exception as e:
        print("Trend error:", e)
        return "The hidden psychology behind overthinking 🤯\n\n#Psychology #Mindset #ReelsIndia"

# ==============================
# GET VIDEO FROM pending/
# ==============================

def get_pending_video():
    url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/resources/video"

    response = requests.get(
        url,
        auth=(API_KEY, API_SECRET),
    params={
    "type": "upload",
    "max_results": 1
}
    )

    data = response.json()

    if "resources" not in data or len(data["resources"]) == 0:
        print("No pending videos found.")
        return None, None

    video = data["resources"][0]
    return video["secure_url"], video["public_id"]

# ==============================
# MOVE FILE
# ==============================

def move_asset(public_id, folder):
    timestamp = int(time.time())
    new_public_id = f"{folder}/{public_id.split('/')[-1]}"

    string_to_sign = f"from_public_id={public_id}&to_public_id={new_public_id}&timestamp={timestamp}{API_SECRET}"
    signature = hashlib.sha1(string_to_sign.encode()).hexdigest()

    url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/rename"

    requests.post(
        url,
        data={
            "from_public_id": public_id,
            "to_public_id": new_public_id,
            "api_key": API_KEY,
            "timestamp": timestamp,
            "signature": signature,
            "resource_type": "video"
        }
    )

# ==============================
# FACEBOOK POST
# ==============================

def post_facebook(video_url, caption):
    res = requests.post(
        f"{GRAPH_URL}/{FB_PAGE_ID}/videos",
        data={
            "file_url": video_url,
            "description": caption,
            "published": "false",
            "access_token": ACCESS_TOKEN
        }
    ).json()

    print("FB:", res)
    return "error" not in res

# ==============================
# INSTAGRAM POST
# ==============================

def post_instagram(video_url, caption):
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
        return False

    publish = requests.post(
        f"{GRAPH_URL}/{IG_BUSINESS_ID}/media_publish",
        data={
            "creation_id": container["id"],
            "access_token": ACCESS_TOKEN
        }
    ).json()

    print("IG Publish:", publish)
    return "error" not in publish

# ==============================
# MAIN
# ==============================

def main():
    video_url, public_id = get_pending_video()

    if not video_url:
        return

    caption = generate_trending_caption()

    fb_success = post_facebook(video_url, caption)
    ig_success = post_instagram(video_url, caption)

    if fb_success and ig_success:
        move_asset(public_id, "uploaded")
        print("✅ Posted successfully → moved to uploaded/")
    else:
        move_asset(public_id, "failed")
        print("❌ Error → moved to failed/")

if __name__ == "__main__":
    main()
