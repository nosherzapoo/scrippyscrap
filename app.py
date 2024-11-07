from flask import Flask, render_template, request, send_file, jsonify, Response
import praw
import pandas as pd
from datetime import datetime
import prawcore
from concurrent.futures import ThreadPoolExecutor
import asyncio
import os
import io
import certifi
import requests
import time
from os import environ
from dotenv import load_dotenv
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch
import numpy as np

# Load environment variables
load_dotenv()

# Configure for serverless
if os.getenv('VERCEL_ENV') == 'production':
    app = Flask(__name__, 
                static_folder='static',
                static_url_path='/static')
else:
    app = Flask(__name__)

# Disable GPU for transformers
os.environ['CUDA_VISIBLE_DEVICES'] = ''

# Initialize RoBERTa model and tokenizer
MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)

def analyze_sentiment(text, include_score=False):
    """Analyze sentiment using RoBERTa model"""
    try:
        encoded_text = tokenizer(text, return_tensors='pt', truncation=True, max_length=512)
        
        with torch.no_grad():
            output = model(**encoded_text)
            scores = torch.nn.functional.softmax(output.logits, dim=1)
            scores = scores.numpy()[0]
        
        sentiment_score = np.argmax(scores)
        confidence = float(scores[sentiment_score])
        
        sentiment_map = {0: 'Negative', 1: 'Neutral', 2: 'Positive'}
        sentiment = sentiment_map[sentiment_score]
        
        result = {
            'sentiment': sentiment,
            'sentiment_confidence': confidence
        }
        
        if include_score:
            polarity = float(scores[2] - scores[0])
            result['sentiment_score'] = polarity
            
        return result
    except Exception as e:
        print(f"Error in sentiment analysis: {e}")
        result = {
            'sentiment': 'Unknown',
            'sentiment_confidence': 0
        }
        if include_score:
            result['sentiment_score'] = 0
        return result

def process_post(post, include_sentiment=False, include_sentiment_score=False):
    """Process a single post and return its data"""
    try:
        current_date = datetime.fromtimestamp(post.created_utc)
        data = {
            'post_id': post.id,
            'title': post.title,
            'text': post.selftext,
            'url': post.url,
            'score': post.score,
            'upvote_ratio': post.upvote_ratio,
            'num_comments': post.num_comments,
            'created_utc': current_date,
            'author': str(post.author),
            'subreddit': post.subreddit.display_name,
            'permalink': post.permalink,
            'is_original_content': post.is_original_content,
            'is_self': post.is_self,
            'stickied': post.stickied
        }
        
        if include_sentiment:
            text = f"{post.title} {post.selftext}"
            sentiment_data = analyze_sentiment(text, include_sentiment_score)
            data.update(sentiment_data)
            
        return data
    except Exception as e:
        print(f"\nError processing post: {e}")
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/scrape', methods=['GET', 'POST'])
def scrape():
    form_data = dict(request.form) if request.method == 'POST' else dict(request.args)
    
    # Get Reddit API credentials
    client_id = form_data.get('client_id')
    client_secret = form_data.get('client_secret')
    username = form_data.get('username')
    password = form_data.get('password')
    
    # Get scraping options
    subreddit_name = form_data.get('subreddit')
    max_posts = int(form_data.get('max_posts', 100))
    include_sentiment = form_data.get('include_sentiment') == 'true'
    include_sentiment_score = form_data.get('include_sentiment_score') == 'true'

    def generate():
        try:
            # Initialize Reddit instance with credentials and default user agent
            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent='Script:RedditScraper:v1.0 (by /u/YourUsername)',
                username=username,
                password=password
            )
            
            subreddit = reddit.subreddit(subreddit_name)
            posts_data = []
            posts_processed = 0

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for post in subreddit.new(limit=max_posts):
                    futures.append(
                        executor.submit(process_post, post, include_sentiment, include_sentiment_score)
                    )
                    posts_processed += 1

                    # Update progress
                    progress = (posts_processed / max_posts) * 100
                    if posts_processed % 10 == 0:
                        yield f"data: {progress}\n\n"

                # Process completed futures
                for future in futures:
                    result = future.result()
                    if result:
                        posts_data.append(result)

            if posts_data:
                df = pd.DataFrame(posts_data)
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                
                yield f"data: 100\n\n"
                yield f"data: DONE\n\n"
            else:
                yield "data: ERROR: No posts were found or processed\n\n"

        except Exception as e:
            yield f"data: ERROR: {str(e)}\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/download', methods=['POST'])
def download():
    try:
        # Get form data (same as before)
        subreddit_name = request.form['subreddit']
        client_id = request.form['client_id']
        client_secret = request.form['client_secret']
        username = request.form['username']
        password = request.form['password']
        max_posts = min(int(request.form['max_posts']), 1000)
        include_sentiment = request.form.get('include_sentiment') == 'true'
        include_sentiment_score = request.form.get('include_sentiment_score') == 'true'
        
        # Initialize Reddit API connection
        try:
            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent='python:reddit_scraper:v1.0',
                username=username,
                password=password,
                requestor_kwargs={'session': requests.Session()}
            )
            # Disable SSL verification for the session (for development only)
            reddit._core._requestor._http.verify = False
            
            # Test authentication
            reddit.user.me()
        except Exception as e:
            return jsonify({'error': f'Failed to authenticate with Reddit: {str(e)}'}), 500

        posts_data = []
        try:
            subreddit = reddit.subreddit(subreddit_name)
            subreddit.id  # Test if subreddit exists
        except Exception as e:
            return jsonify({'error': f'Failed to access subreddit: {str(e)}'}), 500

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for post in subreddit.new(limit=max_posts):
                futures.append(
                    executor.submit(process_post, post, include_sentiment, include_sentiment_score)
                )

            for future in futures:
                result = future.result()
                if result:
                    posts_data.append(result)

        if not posts_data:
            return jsonify({'error': 'No posts were found or processed'}), 500

        # Create DataFrame and save to CSV
        df = pd.DataFrame(posts_data)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)

        return send_file(
            io.BytesIO(csv_buffer.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'{subreddit_name}_posts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

