# C:\Users\rajas\OneDrive\Desktop\Final Year Project V1\ternding_Topics.py

import re
from sklearn.feature_extraction.text import CountVectorizer
from nltk.corpus import stopwords
import nltk # Import nltk to handle potential download requirement

def extract_trending_topics(comments, top_n=5):
    """
    Extracts trending topics from a list of comments using word counts.

    Args:
        comments (list): A list of comment strings.
        top_n (int): The number of top topics to extract.

    Returns:
        list: A list of strings representing the top trending topics.
              Returns an empty list if no topics can be extracted.
    """
    # --- ADDED: Check if the comments list is empty ---
    if not comments:
        print("Warning: No comments provided. Cannot extract trending topics.")
        return []

    # Combine all comments into one long string.
    text = ' '.join(comments)

    # --- ADDED: Check if the combined text is empty before cleaning ---
    if not text:
        print("Warning: Combined comment text is empty. Cannot extract trending topics.")
        return []

    # Remove punctuation and convert text to lowercase.
    text = re.sub(r'[^a-zA-Z\s]', '', text.lower())

    # --- ADDED: Check if the text is empty or contains only whitespace AFTER cleaning ---
    if not text or text.isspace():
        print("Warning: Input text became empty or contains only whitespace after cleaning. Cannot extract trending topics.")
        return []

    # Get English stopwords from nltk.
    try:
        stop_words = stopwords.words('english')
    except LookupError:
        # --- ADDED: Handle case where NLTK stopwords are not downloaded ---
        print("NLTK stopwords not found. Attempting to download...")
        try:
            nltk.download('stopwords')
            stop_words = stopwords.words('english')
            print("NLTK stopwords downloaded successfully.")
        except Exception as e:
            print(f"Failed to download NLTK stopwords: {e}")
            print("Proceeding without stop words, but results may include common words.")
            stop_words = [] # Use an empty list if download fails


    # Use CountVectorizer to count word occurrences, excluding stopwords.
    # The vectorizer will raise ValueError if the text results in an empty vocabulary after processing (including stop words removal)
    vectorizer = CountVectorizer(stop_words=stop_words)

    try:
        # Fit and transform the text. We wrap text in a list because fit_transform expects an iterable of documents.
        X = vectorizer.fit_transform([text])

        # --- ADDED: Check if the vocabulary is empty AFTER fitting ---
        # This is the direct cause of the ValueError we saw before.
        # It means even after processing and stop word removal, no terms were found.
        if not vectorizer.vocabulary_:
             print("Warning: Empty vocabulary created after vectorization (likely due to stop words or minimal content). Cannot extract trending topics.")
             return []

        # Convert the sparse matrix to a dense array.
        word_counts = X.toarray().flatten()

        # Get the list of words from the vectorizer.
        words = vectorizer.get_feature_names_out()

        # --- ADDED: Basic check for words list and word_counts length consistency ---
        if len(words) != len(word_counts):
             print("Error: Mismatch between words and counts after vectorization. Cannot extract trending topics.")
             return []

        # Zip words with their counts and sort by frequency (highest first).
        word_freq = sorted(zip(words, word_counts), key=lambda x: x[1], reverse=True)

        # Filter out words that appear only once (if desired) and pick the top n words.
        # The original code filtered words with count > 1 *before* slicing
        filtered_word_freq = [word for word, count in word_freq if count > 1]

        # --- ADDED: Check if there are any words left after filtering by count > 1 ---
        if not filtered_word_freq:
            print("Warning: No words appeared more than once. Cannot extract trending topics.")
            return []

        # Extract only the words for the top_n topics from the filtered list
        # Ensure top_n does not exceed the number of available words after filtering
        trending_topics = [word for word in filtered_word_freq][:top_n]

        return trending_topics

    except ValueError as e:
        # --- ADDED: Catch the specific ValueError explicitly ---
        if "empty vocabulary" in str(e):
            print("Warning: Empty vocabulary error caught during CountVectorizer fit_transform. Handling gracefully.")
            return [] # Return empty list if the specific error occurs
        else:
            # Re-raise any other ValueErrors
            raise e

    except Exception as e:
        # --- ADDED: Catch any other unexpected errors during the process ---
        print(f"An unexpected error occurred during trending topic extraction: {e}")
        return []


