import streamlit as st
import praw
import pandas as pd
from datetime import datetime
import prawcore
from concurrent.futures import ThreadPoolExecutor
import requests
import time
import io

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
        st.error(f"Error processing post: {e}")
        return None

# Page config
st.set_page_config(page_title="Reddit Scraper", layout="wide")
st.title('Reddit Scraper')

# Form inputs
with st.form("reddit_form"):
    subreddit_name = st.text_input('Subreddit Name')
    client_id = st.text_input('Reddit Client ID')
    client_secret = st.text_input('Reddit Client Secret', type='password')
    username = st.text_input('Reddit Username')
    password = st.text_input('Reddit Password', type='password')
    max_posts = st.number_input('Maximum Posts to Scrape (1-1000)', min_value=1, max_value=1000, value=100)
    
    submitted = st.form_submit_button("Start Scraping")

if submitted:
    try:
        # Progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Initialize Reddit API
        try:
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
            
            # Test authentication
            time.sleep(1)
            reddit.user.me()
            
        except prawcore.exceptions.ResponseException as e:
            if e.response.status_code == 502:
                st.error("Reddit servers are currently unavailable. Please try again in a few minutes.")
            else:
                st.error(f"Reddit API error: {e.response.status_code} - {str(e)}")
            st.stop()
        except prawcore.exceptions.OAuthException:
            st.error("Invalid Reddit credentials")
            st.stop()
        except Exception as e:
            st.error(f"Failed to connect to Reddit: {str(e)}")
            st.stop()

        try:
            subreddit = reddit.subreddit(subreddit_name)
            # Test if subreddit exists
            subreddit.id
        except prawcore.exceptions.Redirect:
            st.error("Subreddit not found")
            st.stop()
        except Exception as e:
            st.error(f"Failed to access subreddit: {str(e)}")
            st.stop()

        posts_data = []
        posts_processed = 0

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for post in subreddit.new(limit=max_posts):
                futures.append(executor.submit(process_post, post))
                posts_processed += 1
                
                # Update progress
                progress = (posts_processed / max_posts)
                progress_bar.progress(progress)
                status_text.text(f"Processing post {posts_processed} of {max_posts}")

            # Process completed futures
            for future in futures:
                result = future.result()
                if result:
                    posts_data.append(result)

        if posts_data:
            # Create DataFrame
            df = pd.DataFrame(posts_data)
            
            # Success message
            st.success(f"Successfully scraped {len(posts_data)} posts!")
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"{subreddit_name}_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime='text/csv'
            )
            
            # Show preview
            st.write("Preview of scraped data:")
            st.dataframe(df)
        else:
            st.error("No posts were found or processed")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")