from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import re
from typing import List, Union, Dict, Any
from langchain_core.tools import tool
import logging

logger = logging.getLogger(__name__)

def extract_video_id(url: str) -> str:
    """
    Extracts the YouTube video ID from a URL.

    Args:
    url: The YouTube video URL

    Returns:
    The video ID as a string, or None if extraction fails
    """
    # Regular expressions for different YouTube URL formats
    patterns = [
        r"(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/|youtube\.com\/watch\?.*v=)([^&\n?#]+)",
        r"(?:youtube\.com\/shorts\/)([^&\n?#]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def _format_timestamp(seconds: float) -> str:
    """
    Converts seconds to timestamp format MM:SS
    """
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"


def _fetch_transcript(video_id: str) -> str:
    """
    Helper function to fetch and format a transcript for a given video ID.

    Args:
        video_id: The YouTube video ID

    Returns:
        Formatted transcript text
    """
    try:
        # Get available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try to get English transcript
        try:
            transcript = transcript_list.find_transcript(["en"])
        except:
            # If English transcript is not available, try to get any transcript and translate it
            try:
                transcript = transcript_list.find_transcript(["en-US", "en-GB"])
            except:
                try:
                    # Get any available transcript and translate to English
                    transcript = next(
                        transcript_list._manually_created_transcripts.values().__iter__()
                    )
                    transcript = transcript.translate("en")
                except:
                    return "Error: No transcript available for this video."

        # Get the transcript data
        transcript_data = transcript.fetch()

        # Format transcript with timestamps (limit to first 2000 words to save tokens)
        formatted_lines = []
        word_count = 0
        max_words = 2000  # Limit transcript length
        
        for entry in transcript_data:
            try:
                timestamp = _format_timestamp(float(entry.start))
                text = entry.text
                words = text.split()
                
                # Check if adding this entry would exceed word limit
                if word_count + len(words) > max_words:
                    # Add partial entry if it fits
                    remaining_words = max_words - word_count
                    if remaining_words > 0:
                        partial_text = " ".join(words[:remaining_words])
                        formatted_lines.append(f"[{timestamp}] {partial_text}...")
                    break
                
                formatted_lines.append(f"[{timestamp}] {text}")
                word_count += len(words)
                
            except AttributeError:
                timestamp = _format_timestamp(float(entry["start"]))
                text = entry["text"]
                words = text.split()
                
                if word_count + len(words) > max_words:
                    remaining_words = max_words - word_count
                    if remaining_words > 0:
                        partial_text = " ".join(words[:remaining_words])
                        formatted_lines.append(f"[{timestamp}] {partial_text}...")
                    break
                
                formatted_lines.append(f"[{timestamp}] {text}")
                word_count += len(words)

        return "\n".join(formatted_lines)
        
    except Exception as e:
        logger.error(f"Error fetching transcript for video {video_id}: {e}")
        return f"Error fetching transcript: {str(e)}"


@tool
def get_youtube_transcript(url: str) -> str:
    """
    Fetches the transcript of a YouTube video in English given its URL.

    Args:
        url: The URL of the YouTube video

    Returns:
        String containing the transcript of the video in English with timestamps
    """
    try:
        logger.info(f"Fetching transcript for URL: {url}")
        
        # Extract video ID from the URL
        video_id = extract_video_id(url)
        if not video_id:
            error_msg = "Error: Could not extract video ID from the provided URL."
            logger.error(error_msg)
            return error_msg

        transcript = _fetch_transcript(video_id)
        
        # Add video metadata (we'll get this from the URL for now)
        video_info = f"""YOUTUBE VIDEO: {url}
Video ID: {video_id}
Transcript (first 2000 words):"""
        
        full_output = f"{video_info}\n\n{transcript}"
        logger.info(f"Successfully fetched transcript for video {video_id}")
        return full_output

    except Exception as e:
        error_msg = f"Error fetching transcript: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
def get_multiple_youtube_transcripts(urls: List[str]) -> str:
    """
    Fetches transcripts for multiple YouTube videos given their URLs.

    Args:
        urls: A list of YouTube video URLs

    Returns:
        String containing all transcripts with timestamps, separated by dividers
    """
    try:
        if not urls or not isinstance(urls, list):
            error_msg = "Error: No valid URLs provided."
            logger.error(error_msg)
            return error_msg

        logger.info(f"Processing {len(urls)} YouTube URLs")
        results = []

        for i, url in enumerate(urls, 1):
            logger.info(f"Processing video {i}/{len(urls)}: {url}")
            transcript = get_youtube_transcript(url)
            results.append(f"URL: {url}\n\n{transcript}")

        # Join all transcripts with divider
        divider = "\n\n" + "=" * 80 + "\n\n"
        combined_result = divider.join(results)
        
        logger.info(f"Successfully processed {len(urls)} YouTube videos")
        return combined_result
        
    except Exception as e:
        error_msg = f"Error processing multiple YouTube transcripts: {str(e)}"
        logger.error(error_msg)
        return error_msg
