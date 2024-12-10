import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
import pandas as pd
from datetime import datetime

# Load RoBERTa model and tokenizer
tokenizer = AutoTokenizer.from_pretrained("cardiffnlp/twitter-roberta-base-sentiment")
model = AutoModelForSequenceClassification.from_pretrained("cardiffnlp/twitter-roberta-base-sentiment")

def analyze_sentiment(text):
    # Handle non-string inputs
    if pd.isna(text) or not isinstance(text, str):
        return 'Unknown', 0.0
        
    # Encode text and run through model
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    outputs = model(**inputs)
    
    # Get prediction
    predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
    sentiment_scores = predictions[0].detach().numpy()
    
    # Map scores to labels
    labels = ['Negative', 'Neutral', 'Positive']
    sentiment = labels[np.argmax(sentiment_scores)]
    confidence = np.max(sentiment_scores)
    
    return sentiment, confidence

# Read the CSV files
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
posts_df = pd.read_csv(f'final_posts_output.csv')

# Analyze post sentiments
print("Analyzing post sentiments...")
total_posts = len(posts_df)
for idx, row in posts_df.iterrows():
    sentiment, confidence = analyze_sentiment(row['text'])
    posts_df.at[idx, 'sentiment'] = sentiment
    posts_df.at[idx, 'sentiment_confidence'] = confidence
    if (idx + 1) % 10 == 0:  # Print progress every 10 posts
        progress = ((idx + 1) / total_posts) * 100
        print(f"Progress: {progress:.1f}% ({idx + 1}/{total_posts} posts analyzed)")

# Analyze comment sentiments
print("Analyzing comment sentiments...")

# Save updated DataFrames with sentiment analysis
posts_df.to_csv(f'dollar_general_posts_with_sentiment_{timestamp}.csv', index=False)

# Print summary statistics
print("\nPost Sentiment Distribution:")
print(posts_df['sentiment'].value_counts())
print("\nComment Sentiment Distribution:")

# Calculate average sentiment confidence
print(f"\nAverage Post Sentiment Confidence: {posts_df['sentiment_confidence'].mean():.2f}")