from flask import render_template
from database import Database

db = Database()


def render_dashboard(username, error_message=None, modal_data=None):
    """Renders the full dashboard page HTML for the given logged-in username."""
    profile_image_b64 = db.get_user_profile_image(username)
    video_ids, video_titles = db.get_user_video_ids(username)
    videos = [
        {"video_id": vid, "Video_Title": title}
        for vid, title in zip(video_ids, video_titles)
    ]
    return render_template(
        'index.html',
        username=username,
        videos=videos,
        profile=profile_image_b64,
        error_message=error_message,
        modal_data=modal_data,
    )
