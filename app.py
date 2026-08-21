from dotenv import load_dotenv
load_dotenv()

import os
from flask import Flask, render_template, request, session, redirect, url_for, flash
from auth import auth
from database import Database
from dashboard import render_dashboard
from analyses import perform_video_analysis  # helper function in a separate module
from extract_id import extract_video_id  # needed to extract video id

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]
app.register_blueprint(auth)
db = Database()

# New Landing Page Route
@app.route('/')
def landing():
    """Renders the landing page."""
    # You will need to create a 'landing.html' template file
    return render_template('landing.html')

# Existing Dashboard Route (formerly '/')
@app.route('/dashboard')
def index():
    """Renders the user dashboard after login."""
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    return render_dashboard(session.get('user'))

# New About Us Page Route
@app.route('/about')
def about():
    """Renders the About Us page."""
    # You will need to create an 'about.html' template file
    return render_template('about.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    """Handles video analysis requests."""
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    video_link = request.form['video_link']

    # Extract the video ID from the link.
    video_id = extract_video_id(video_link)
    # NOTE: The specific format check in the error message might need adjustment
    # depending on the actual format your extract_video_id function expects.
    # The current error message seems specific to a tool output format,
    # not a standard YouTube URL.
    if not video_id:
        error_alert = '''
            <div class="rounded-brand-sm px-4 py-3 text-sm font-medium bg-negative/10 text-negative border border-negative/30" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i><strong>Error:</strong> The YouTube link you entered is not valid. Please check the URL and try again.
            </div>
        '''
        return render_dashboard(session.get('user'), error_message=error_alert)

    # Check if the user has already analyzed this video
    existing_data = db.get_analysis_for_user(session.get('user'), video_id)

    if existing_data:
        # Prepare structured data for modal display
        modal_data = {
            "video_id": video_id,
            "Video_Title":existing_data.get("Video_Title"),
            "Channel_Name": existing_data.get("Channel_Name"),
            "total_fetched": existing_data.get("total_fetched", 0),
            "total_english": existing_data.get("total_english", 0),
            "positive_count": existing_data.get("positive_count", 0),
            "negative_count": existing_data.get("negative_count", 0),
            "neutral_count": existing_data.get("neutral_count", 0),
            "positive_emoji": existing_data.get("pos_count", 0),
            "negative_emoji": existing_data.get("neg_count", 0),
            "neutral_emoji": existing_data.get("neu_count", 0),
            "trending_topics": existing_data.get("trending_topics", []),
            "bar_chart_id": existing_data.get("bar_chart_id", None),
            "emoji_chart_id": existing_data.get("emoji_chart_id", None),
            "key_insights": existing_data.get("key_insights"),
            "thumbnail": existing_data.get("thumbnail")
        }

        return render_dashboard(session.get('user'), modal_data=modal_data)

    else:
        # Perform new analysis
        results, analysis_data = perform_video_analysis(video_link)
        if not results:
            error_alert = f'''
                <div class="rounded-brand-sm px-4 py-3 text-sm font-medium bg-negative/10 text-negative border border-negative/30" role="alert">
                    <i class="fas fa-exclamation-triangle me-2"></i><strong>Error:</strong> {analysis_data}
                </div>
            '''
            return render_dashboard(session.get('user'), error_message=error_alert)

        # Save new analysis in the database
        db.save_analysis(session.get('user'), results["video_id"], analysis_data, results["bar_chart"], results["emoji_chart"])

        # Prepare structured data for modal display
        modal_data = {
            "video_id": results["video_id"],
            "Video_Title":analysis_data.get("Video_Title"),
            "Channel_Name": analysis_data.get("Channel_Name"),
            "total_fetched": analysis_data.get("total_fetched", 0),
            "total_english": analysis_data.get("total_english", 0),
            "positive_count": analysis_data.get("positive_count", 0),
            "negative_count": analysis_data.get("negative_count", 0),
            "neutral_count": analysis_data.get("neutral_count", 0),
            "positive_emoji": analysis_data.get("pos_count", 0),
            "negative_emoji": analysis_data.get("neg_count", 0),
            "neutral_emoji": analysis_data.get("neu_count", 0),
            "trending_topics": analysis_data.get("trending_topics", []),
            "bar_chart_id": results.get("bar_chart"),
            "emoji_chart_id": results.get("emoji_chart"),
            "key_insights": analysis_data.get("key_insights"),
            "thumbnail": analysis_data.get("thumbnail")
        }

        return render_dashboard(session.get('user'), modal_data=modal_data)

@app.route('/history')
def history():
    """Displays the analysis history for the logged-in user."""
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    user_id = session.get('user')
    history_data = db.get_user_analysis_history(user_id)
    profile_image_b64 = db.get_user_profile_image(user_id)
    return render_template('History_model.html', history_data=history_data, username=user_id, profile=profile_image_b64)

@app.route('/delete_history/<video_id>', methods=['POST'])
def delete_history(video_id):
    """Deletes a specific video analysis history record for the logged-in user."""
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    user_id = session.get('user')
    deleted = db.delete_analysis(user_id, video_id)
    if deleted:
        flash('Analysis history deleted successfully.', 'success')
    else:
        flash('Failed to delete analysis history.', 'error')
    return redirect(url_for('history'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')