from urllib.parse import urlparse, parse_qs
def extract_video_id(url):
    """
    Extract the video ID from a YouTube URL.
    """
    parsed_url = urlparse(url)

    # Check for standard YouTube URL
    if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
        query_params = parse_qs(parsed_url.query)
        if 'v' in query_params:
            return query_params['v'][0]

    # Check for shortened YouTube URL
    if parsed_url.hostname in ['youtu.be']:
        return parsed_url.path.lstrip('/')

    return None
    