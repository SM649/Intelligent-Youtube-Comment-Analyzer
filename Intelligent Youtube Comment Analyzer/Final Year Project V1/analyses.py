import numpy as np
from extract_id import extract_video_id
from fetch_comments import fetch_comments
from create_bar_chart import create_sentiment_barchart, create_emoji_barchart
from separate_emojis_and_text import separate_emojis_and_text
from Model import analyze_sentiment_distilbert
from emoji_analyzer import analyze_comments_with_emojis
from ternding_Topics import extract_trending_topics 
from key_insights import summarize_comments

def perform_video_analysis(video_link):
    """
    Perform all analysis steps for a given video link.
    
    Steps:
      - Extract the video ID from the link.
      - Fetch comments and basic statistics.
      - Separate emoji content from text.
      - Perform sentiment analysis on text comments.
      - Perform emoji sentiment analysis.
      - Generate charts as base64 strings.
      - Build HTML snippets for display.
    
    Returns:
      A tuple (results_dict, analysis_data) if successful.
      If video link is invalid, returns (None, error_message).
    """
    video_id = extract_video_id(video_link)
    if not video_id:
        return None, "Invalid YouTube link."

    # Fetch comments from the video
    comments, total_fetched, total_english,video_title, channel_name, tumbnail = fetch_comments(video_id)
    comments_emoji = separate_emojis_and_text(comments)
    comments_text = comments_emoji.get('texts', [])

    # Analyze emojis in the comments
    classified_emojis = analyze_comments_with_emojis(comments)
    pos_emj = len(classified_emojis.get("positive_comments", []))
    neg_emj = len(classified_emojis.get("negative_comments", []))
    neu_emj = len(classified_emojis.get("neutral_comments", []))

    # Analyze text sentiment using a DistilBERT model
    sentiment_results = analyze_sentiment_distilbert(comments_text)
    positive_count = sum(1 for p in sentiment_results if p == 1)
    negative_count = sum(1 for p in sentiment_results if p == -1)
    neutral_count  = sum(1 for p in sentiment_results if p not in [1, -1])

    # Generate charts (as base64 image strings)
    bar_chart = create_sentiment_barchart(positive_count, negative_count, neutral_count)
    emoji_chart = create_emoji_barchart(pos_emj, neg_emj, neu_emj)

    # Build HTML string for text sentiment analysis results
    sentiment_info = f"""
        <h4 class="c-t">Sentiment Analysis Results:</h4>
        <p class="c-t">Total Comments Fetched: {total_fetched}</p>
        <p class="c-t">Total English Comments: {total_english}</p>
        <p class="c-t">Positive Comments: {positive_count}</p>
        <p class="c-t">Negative Comments: {negative_count}</p>
        <p class="c-t">Neutral Comments: {neutral_count}</p>
    """

    # Build HTML string for trending topics
    trending_topics = extract_trending_topics(comments_text, top_n=5)
    topics_html = "<h4 class='c-t'>Trending Topics:</h4><ul>"
    for topic in trending_topics:
        topics_html += f"<li class='c-t'>{topic}</li>"
    topics_html += "</ul>"

    # Build HTML string for emoji sentiment analysis results
    emoji_result = f"""
        <h3 class="c-t">Emoji Sentiment Analysis:</h3>
        <p class="c-t">Positive Emojis: {pos_emj}</p>
        <p class="c-t">Negative Emojis: {neg_emj}</p>
        <p class="c-t">Neutral Emojis: {neu_emj}</p>
    """

    # Generate key insights summary
    key_insights_summary = summarize_comments(comments_text)
    insights_html = f"<h4 class='c-t'>Key Insights:</h4><p class='c-t'>{key_insights_summary}</p>"

    # Pack display data into a dictionary (to be sent to the template)
    results_dict = {
        "video_id": video_id,
        "sentiment_info": sentiment_info,
        "trend_t": topics_html,
        "emoji_result": emoji_result,
        "bar_chart": bar_chart,
        "emoji_chart": emoji_chart,
        "comments_text": comments_text,
        "key_insights": insights_html, # Add the key insights HTML
        "thumbnail": tumbnail
    }

    # Pack raw analysis data into a dictionary (to be saved in the database)
    analysis_data = {
        "Video_Title": video_title,
        "Channel_Name":channel_name,
        "total_fetched": total_fetched,
        "total_english": total_english,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "pos_count": pos_emj,
        "neg_count": neg_emj,
        "neu_count": neu_emj,
        "trending_topics": trending_topics,
        "key_insights": key_insights_summary, # Add the raw key insights summary
        "thumbnail": tumbnail
    }

    return results_dict, analysis_data