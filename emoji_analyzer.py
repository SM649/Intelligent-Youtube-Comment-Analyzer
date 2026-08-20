from transformers import pipeline
import emoji
import re # Keeping original imports as requested

# Keeping these function definitions as requested.
def contains_emoji(text):
   
    if not isinstance(text, str):
        return False
    return emoji.emoji_count(text) > 0

def is_only_emoji(text):
    
    if not isinstance(text, str):
        return False

    # Remove all whitespace for a cleaner check
    text_no_whitespace = "".join(text.split())

    # If after removing whitespace, the string is empty, it wasn't just emojis
    if not text_no_whitespace:
        return False

    # Check if every character in the non-whitespace string is an emoji
    return all(emoji.is_emoji(char) for char in text_no_whitespace)


def analyze_comments_with_emojis(comments):
    
    try:
        # Using a model fine-tuned on tweets that provides negative, neutral, positive labels
        sentiment_analyzer = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment", framework="pt")
        # print("Sentiment analysis model loaded within function.") # Optional: for debugging
    except Exception as e:
        print(f"Error loading sentiment analysis model within function: {e}")
        print("Sentiment analysis cannot be performed.")
        # Return empty lists if model fails to load
        return {
            "positive_comments": [],
            "negative_comments": [],
            "neutral_comments": []
        }


    # Issue 8 addressed: Basic input validation
    if not isinstance(comments, list):
        print("Error: Input 'comments' must be a list.")
        return {
            "positive_comments": [],
            "negative_comments": [],
            "neutral_comments": []
        }

    # Define lists to store the comments based on their sentiment
    positive_comments = []
    negative_comments = []
    neutral_comments = []
    # Removed emoji_only_comments list initialization

    # Loop through each comment
    for comment in comments:
         # Ensure the comment is a string before processing
        if not isinstance(comment, str):
            print(f"Skipping non-string element: {comment}")
            # Non-string elements are ignored as they cannot contain emojis
            continue

        # Only process comments that contain ANY emojis
        # Comments without emojis are skipped/ignored in the else block.
        if contains_emoji(comment):
             # Add error handling around sentiment analysis
            try:
                # Analyze the sentiment of the comment
                result = sentiment_analyzer(comment)
                # This model's output labels are 'LABEL_0', 'LABEL_1', 'LABEL_2'
                sentiment = result[0]['label']

                # --- CHANGED LABEL CHECKS HERE ---
                # Map 'LABEL_0' (Negative), 'LABEL_1' (Neutral), 'LABEL_2' (Positive)
                if sentiment == "LABEL_2": # LABEL_2 corresponds to Positive
                    positive_comments.append(comment)
                elif sentiment == "LABEL_0": # LABEL_0 corresponds to Negative
                    negative_comments.append(comment)
                elif sentiment == "LABEL_1": # LABEL_1 corresponds to Neutral
                    neutral_comments.append(comment)
                else:
                     # This else should not be hit with standard outputs but acts as a safeguard
                    print(f"Warning: Unrecognized sentiment label '{sentiment}' for comment: {comment}")
                    # Default to neutral for unknown labels
                    neutral_comments.append(comment)

            except Exception as e:
                print(f"Error analyzing sentiment for comment '{comment}': {e}")
                # If analysis fails for a comment with emojis, add to neutral
                neutral_comments.append(comment)
        else:
            # Comments without emojis are IGNORED
            pass



    return {
        "positive_comments": positive_comments,
        "negative_comments": negative_comments,
        "neutral_comments": neutral_comments
    }
