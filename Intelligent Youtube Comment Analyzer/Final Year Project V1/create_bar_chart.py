import matplotlib.pyplot as plt
import io
import base64

def create_sentiment_barchart(positive, negative, neutral):
    # Create the bar chart
    categories = ['Negative', 'Positive', 'Neutral']
    values = [negative, positive, neutral]

    darker_colors = ['#dc3545', '#28a745', '#ffc107'] # DarkRed, DarkGreen, DarkGray

    
    plt.figure(figsize=(5, 3))
    plt.bar(categories, values, color=darker_colors, width=0.4)
    plt.title('Sentiment Analysis of Comments')
    plt.xlabel('Sentiment')
    plt.ylabel('Number Analyzed of Comments')
    
    # Save the chart to a BytesIO object
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png')
    plt.close()
    
    # Rewind the buffer's position to the beginning
    img_buffer.seek(0)
    
    # Open the image using PIL for further use or return
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
    
    return img_base64

def create_emoji_barchart(positive, negative, neutral):
    
    categories = ['Negative', 'Positive', 'Neutral']
    values = [negative, positive, neutral]

    # Define darker shades for colors
    darker_colors = ['#dc3545', '#28a745', '#ffc107'] # DarkRed, DarkGreen, DarkGray

    plt.figure(figsize=(5, 3))
    # Use darker colors and set a smaller bar width (e.g., 0.6)
    plt.bar(categories, values, color=darker_colors, width=0.4)
    plt.title('Emoji Analysis of Comments')
    plt.xlabel(' ')
    plt.ylabel('Number of Emojis Analyzed')

    # Save the chart to a BytesIO object
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png')
    plt.close()

    # Rewind the buffer's position to the beginning
    img_buffer.seek(0)

    # Encode the image to base64
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')

    return img_base64
