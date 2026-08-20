import emoji

def separate_emojis_and_text(comments):
    """
    Separate emojis from text in a list of comments.
    """
    all_texts = []
    all_emojis = []

    for comment in comments:
        text_only = ''.join(char for char in comment if not emoji.is_emoji(char))
        emojis = ''.join(char for char in comment if emoji.is_emoji(char))

        if text_only.strip():  # Adds only if text is non-empty
            all_texts.append(text_only.strip())
        if emojis.strip():  # Adds only if emojis are non-empty
            all_emojis.append(emojis.strip()) # Store each emoji string separately

    return {'texts': all_texts, 'emojis': all_emojis}
