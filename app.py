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
import sslr
import requests
import time

app = Flask(__name__, template_folder='templates')

def process_post(post):
    """Process a single post and return its data"""
    try:
        current_date = datetime.fromtimestamp(post.created_utc)
        return {
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
    except Exception as e:
        print(f"\nError processing post: {e}")
        return None

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reddit Scraper</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            .container {
                background-color: #f5f5f5;
                padding: 20px;
                border-radius: 5px;
            }
            .form-group {
                margin-bottom: 15px;
            }
            label {
                display: block;
                margin-bottom: 5px;
            }
            input {
                width: 100%;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            button:hover {
                background-color: #45a049;
            }
            #progress {
                display: none;
                margin-top: 20px;
            }
            .progress-bar {
                width: 100%;
                height: 20px;
                background-color: #f0f0f0;
                border-radius: 10px;
                overflow: hidden;
            }
            .progress-fill {
                width: 0%;
                height: 100%;
                background-color: #4CAF50;
                transition: width 0.3s ease-in-out;
            }
            .error-message {
                color: red;
                margin-top: 10px;
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Reddit Scraper</h1>
            <form id="scrapeForm" method="POST" action="/scrape">
                <div class="form-group">
                    <label for="subreddit">Subreddit Name:</label>
                    <input type="text" id="subreddit" name="subreddit" required>
                </div>
                <div class="form-group">
                    <label for="client_id">Reddit Client ID:</label>
                    <input type="text" id="client_id" name="client_id" required>
                </div>
                <div class="form-group">
                    <label for="client_secret">Reddit Client Secret:</label>
                    <input type="password" id="client_secret" name="client_secret" required>
                </div>
                <div class="form-group">
                    <label for="username">Reddit Username:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label for="password">Reddit Password:</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <div class="form-group">
                    <label for="max_posts">Maximum Posts to Scrape (1-1000):</label>
                    <input type="number" id="max_posts" name="max_posts" min="1" max="1000" value="100" required>
                </div>
                <button type="submit">Start Scraping</button>
            </form>
            <div id="progress">
                <h3>Scraping Progress:</h3>
                <div class="progress-bar">
                    <div class="progress-fill"></div>
                </div>
            </div>
            <div id="error-message" class="error-message"></div>
        </div>

        <script>
            document.getElementById('scrapeForm').onsubmit = function(e) {
                e.preventDefault();
                
                const progress = document.getElementById('progress');
                const progressFill = document.querySelector('.progress-fill');
                const errorMessage = document.getElementById('error-message');
                
                progress.style.display = 'block';
                errorMessage.style.display = 'none';
                
                // Create URL with query parameters
                const formData = new FormData(this);
                const params = new URLSearchParams(formData);
                const eventSource = new EventSource('/scrape?' + params.toString());
                
                eventSource.onmessage = function(e) {
                    const data = e.data;
                    if (data.startsWith('ERROR:')) {
                        eventSource.close();
                        errorMessage.textContent = data.substring(7);
                        errorMessage.style.display = 'block';
                        progress.style.display = 'none';
                    } else if (data === 'DONE') {
                        eventSource.close();
                        // Submit form to download endpoint
                        const downloadForm = document.createElement('form');
                        downloadForm.method = 'POST';
                        downloadForm.action = '/download';
                        
                        // Copy all form data to the download form
                        for (let pair of formData.entries()) {
                            const input = document.createElement('input');
                            input.type = 'hidden';
                            input.name = pair[0];
                            input.value = pair[1];
                            downloadForm.appendChild(input);
                        }
                        
                        document.body.appendChild(downloadForm);
                        downloadForm.submit();
                        document.body.removeChild(downloadForm);
                        
                        // Reset progress
                        progress.style.display = 'none';
                    } else {
                        const progress = parseFloat(data);
                        progressFill.style.width = progress + '%';
                    }
                };
                
                eventSource.onerror = function() {
                    eventSource.close();
                    errorMessage.textContent = 'An error occurred while scraping. Please try again.';
                    errorMessage.style.display = 'block';
                    progress.style.display = 'none';
                };
            };
        </script>
    </body>
    </html>
    """

@app.route('/scrape', methods=['GET', 'POST'])
def scrape():
    # Store form data before entering generator function
    form_data = dict(request.form) if request.method == 'POST' else dict(request.args)
    
    def generate():
        try:
            # Use stored form_data instead of accessing request directly
            subreddit_name = form_data['subreddit']
            client_id = form_data['client_id']
            client_secret = form_data['client_secret']
            username = form_data['username']
            password = form_data['password']
            max_posts = min(int(form_data['max_posts']), 1000)

            # Initialize Reddit API
            try:
                # Add a more descriptive user agent with your username
                user_agent = f"python:reddit_scraper:v1.0 (by /u/{username})"
                
                reddit = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent=user_agent,
                    username=username,
                    password=password,
                    requestor_kwargs={'session': requests.Session()}
                )
                reddit._core._requestor._http.verify = False
                
                # Add a small delay before authentication
                time.sleep(1)
                
                try:
                    # Test authentication
                    reddit.user.me()
                except prawcore.exceptions.ResponseException as e:
                    if e.response.status_code == 502:
                        yield "data: ERROR: Reddit servers are currently unavailable. Please try again in a few minutes.\n\n"
                    else:
                        yield f"data: ERROR: Reddit API error: {e.response.status_code} - {str(e)}\n\n"
                    return
                except prawcore.exceptions.OAuthException:
                    yield "data: ERROR: Invalid Reddit credentials\n\n"
                    return
                except Exception as e:
                    yield f"data: ERROR: Failed to connect to Reddit: {str(e)}\n\n"
                    return

            except Exception as e:
                yield f"data: ERROR: {str(e)}\n\n"
                return

            try:
                subreddit = reddit.subreddit(subreddit_name)
                # Test if subreddit exists
                subreddit.id
            except prawcore.exceptions.Redirect:
                yield "data: ERROR: Subreddit not found\n\n"
                return
            except Exception as e:
                yield f"data: ERROR: Failed to access subreddit: {str(e)}\n\n"
                return

            posts_data = []
            posts_processed = 0

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for post in subreddit.new(limit=max_posts):
                    futures.append(
                        executor.submit(process_post, post)
                    )
                    posts_processed += 1

                    # Update progress
                    progress = (posts_processed / max_posts) * 100
                    if posts_processed % 10 == 0:  # Update every 10 posts
                        yield f"data: {progress}\n\n"

                # Process completed futures
                for future in futures:
                    result = future.result()
                    if result:
                        posts_data.append(result)

            if posts_data:
                # Create DataFrame and save to CSV
                df = pd.DataFrame(posts_data)
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                
                yield f"data: 100\n\n"  # Send 100% progress
                yield f"data: DONE\n\n"  # Signal completion
            else:
                yield "data: ERROR: No posts were found or processed\n\n"

        except Exception as e:
            yield f"data: ERROR: {str(e)}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream'
    )

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
                futures.append(executor.submit(process_post, post))

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

if __name__ == "__main__":
    # Development
    app.run(debug=True)
else:
    # Production
    app.run()
