import matplotlib.pyplot as plt
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
# Set the backend to 'Agg' to prevent tkinter issues
plt.switch_backend('Agg')
# model_directory = './my_model_directory/'

# os.makedirs(model_directory, exist_ok=True)

tokenizer = AutoTokenizer.from_pretrained("nlptown/bert-base-multilingual-uncased-sentiment")
model = AutoModelForSequenceClassification.from_pretrained("nlptown/bert-base-multilingual-uncased-sentiment")

def analyze_sentiment_distilbert(text_list):
    """
    Analyze the sentiment of a list of comments using a fine-tuned DistilBERT model for multi-class sentiment.
    
    Args:
        text_list (list of str): The list of comments to analyze.

    Returns:
        list of tuple: A list of tuples containing the polarity (1 for positive, -1 for negative, 0 for neutral) 
                       and the subjectivity scores for each comment.
    """
    results = []

    # Loop through each comment in the list
    for text in text_list:
        # Tokenize the input text
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)

        # Get model predictions
        with torch.no_grad():
            outputs = model(**inputs)
        
        # Get the predicted class (1-5)
        predicted_class = torch.argmax(outputs.logits, dim=1).item()

        # Convert predicted class to sentiment
        if predicted_class in [1, 2]:  # 1-2 stars: Negative
            polarity = -1
        elif predicted_class == 3:     # 3 stars: Neutral
            polarity = 0
        else:                          # 4-5 stars: Positive
            polarity = 1
        
        # Append result
        
        results.append((polarity))

    return results