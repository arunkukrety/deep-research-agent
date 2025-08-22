from typing import List, Dict, Any, Optional
import requests
from langchain_core.tools import tool
import logging
import json

logger = logging.getLogger(__name__)

@tool
def get_reddit_comments(url: str) -> str:
    """
    Fetches comments from a Reddit post URL using Reddit's JSON API.
    
    Args:
        url: The Reddit post URL (e.g., https://www.reddit.com/r/ethereum/comments/...)
    
    Returns:
        String containing formatted Reddit post and comments
    """
    logger.info(f"Scraping Reddit post: {url}")
    
    # Ensure URL is in JSON format
    if not url.endswith(".json"):
        url += ".json"

    # Set user agent to avoid being blocked
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Extract post title and content
        post_data = data[0]["data"]["children"][0]["data"]
        post_title = post_data.get("title", "No title")
        post_content = post_data.get("selftext", "No content")
        post_author = post_data.get("author", "Anonymous")
        post_score = post_data.get("score", 0)
        post_subreddit = post_data.get("subreddit", "unknown")
        post_comments_count = post_data.get("num_comments", 0)

        # Extract top comments only (limit to top 5 by score)
        comments = []
        if len(data) > 1 and "children" in data[1]["data"]:
            # Get all comments and sort by score
            all_comments = []
            for comment in data[1]["data"]["children"]:
                if "body" in comment.get("data", {}):
                    author = comment["data"].get("author", "Anonymous")
                    score = comment["data"].get("score", 0)
                    body = comment["data"]["body"]
                    all_comments.append((score, author, body))
            
            # Sort by score (highest first) and take top 5
            all_comments.sort(key=lambda x: x[0], reverse=True)
            top_comments = all_comments[:5]
            
            for score, author, body in top_comments:
                comments.append(f"Author: {author} | Score: {score}\n{body}")

        # Format the output (optimized)
        formatted_output = f"""REDDIT POST: {post_title}
Post Link: {url}
Subreddit: r/{post_subreddit}
Score: {post_score}

Content: {post_content}

"""
        
        if comments:
            formatted_output += "TOP COMMENTS:\n\n"
            formatted_output += "\n\n---\n\n".join(comments)
        else:
            formatted_output += "No comments found."

        logger.info(f"Successfully scraped Reddit post with {len(comments)} comments")
        return formatted_output

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error scraping Reddit: {e}")
        return f"Error fetching Reddit post: {str(e)}"
    except (KeyError, IndexError) as e:
        logger.error(f"Data parsing error: {e}")
        return f"Error parsing Reddit data: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error scraping Reddit: {e}")
        return f"Error: {str(e)}"


@tool
def get_multiple_reddit_posts(urls: List[str]) -> str:
    """
    Fetches comments from multiple Reddit post URLs.
    
    Args:
        urls: A list of Reddit post URLs
    
    Returns:
        String containing formatted Reddit comments from multiple posts
    """
    logger.info(f"Scraping {len(urls)} Reddit posts")
    
    if not urls or not isinstance(urls, list):
        return "Error: No valid URLs provided."

    results = []
    successful_scrapes = 0

    for i, url in enumerate(urls, 1):
        logger.info(f"Scraping post {i}/{len(urls)}: {url}")
        post_data = get_reddit_comments(url)
        
        if not post_data.startswith("Error"):
            successful_scrapes += 1
            
        results.append(f"POST {i}: {url}\n{post_data}")

    # Join all posts with clear separators
    combined_output = "\n\n" + "="*80 + "\n" + "="*80 + "\n\n".join(results)
    
    logger.info(f"Completed scraping: {successful_scrapes}/{len(urls)} posts successful")
    return combined_output


# Test function for development
if __name__ == "__main__":
    # Test with a sample Reddit URL
    test_url = "https://www.reddit.com/r/ethereum/comments/1iuxkmv/how_bybit_could_have_prevented_this_hack_but_didnt/"
    print(get_reddit_comments(test_url))
