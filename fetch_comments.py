import os
import aiohttp
import asyncio
from langid import classify  # Faster alternative to langdetect
import base64

API_KEY = os.environ["YOUTUBE_API_KEY"]
BASE_URL = "https://www.googleapis.com/youtube/v3/commentThreads"
VIDEO_BASE_URL = "https://www.googleapis.com/youtube/v3/videos"

async def fetch_page(session, video_id, page_token=None):
    """
    Fetch a single page of comments from the YouTube Data API asynchronously.
    """
    params = {
        "part": "snippet",
        "videoId": video_id,
        "key": API_KEY,
        "maxResults": 100,
    }
    if page_token:
        params["pageToken"] = page_token

    async with session.get(BASE_URL, params=params) as response:
        response.raise_for_status()
        return await response.json()

async def fetch_thumbnail_base64(session, thumbnail_url):
    """
    Fetches the thumbnail image from the URL and encodes it in Base64.
    """
    try:
        async with session.get(thumbnail_url) as response:
            response.raise_for_status()
            image_data = await response.read()
            return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        print(f"Error fetching thumbnail: {e}")
        return None

async def fetch_video_details(session, video_id):
    """
    Fetch video details (title, channel name, and thumbnail URL) from the YouTube Data API asynchronously.
    """
    params = {
        "part": "snippet",
        "id": video_id,
        "key": API_KEY,
    }
    async with session.get(VIDEO_BASE_URL, params=params) as response:
        response.raise_for_status()
        data = await response.json()
        items = data.get('items', [])
        if items:
            snippet = items[0]['snippet']
            video_title = snippet.get('title', '')
            channel_name = snippet.get('channelTitle', '')
            thumbnails = snippet.get('thumbnails', {})
            # Get the URL of the default resolution thumbnail
            thumbnail_url = thumbnails.get('default', {}).get('url')
            return video_title, channel_name, thumbnail_url
        return None, None, None

async def fetch_comments_async(video_id):
    comments = []
    total_fetched_comments = 0
    total_english_comments = 0
    next_page_token = None
    base64_thumbnail = None

    async with aiohttp.ClientSession() as session:
        # Fetch video title, channel name, and thumbnail URL
        video_title, channel_name, thumbnail_url = await fetch_video_details(session, video_id)

        # Fetch and encode the thumbnail in Base64 if URL is available
        if thumbnail_url:
            base64_thumbnail = await fetch_thumbnail_base64(session, thumbnail_url)

        while total_english_comments < 1000:
            try:
                response = await fetch_page(session, video_id, next_page_token)
                items = response.get('items', [])

                for item in items:
                    comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
                    total_fetched_comments += 1  # Count total fetched comments

                    try:
                        if classify(comment)[0] == 'en':
                            comments.append(comment)
                            total_english_comments += 1

                            if total_english_comments >= 1000:
                                break  # Stop once limit is reached
                    except:
                        continue  # Skip if language detection fails

                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break  # Exit loop if there are no more pages
            except Exception as e:
                print(f"Error fetching page: {e}")
                break  # Exit loop on error

    return comments, total_fetched_comments, total_english_comments, video_title, channel_name, base64_thumbnail


# Main Function to Run the Async Code
def fetch_comments(video_id):
    return asyncio.run(fetch_comments_async(video_id))