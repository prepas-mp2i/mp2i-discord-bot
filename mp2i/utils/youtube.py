import logging
import os
from typing import Generator

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


def search(query: str, n=1) -> Generator[dict, None, None]:
    """
    Search video on YouTube matching the query
    """
    try:
        youtube = build("youtube", "v3", developerKey=os.getenv("API_DEVELOPER_KEY"))
        response = (
            youtube.search()
            .list(part="snippet", q=query, type="video", maxResults=n)
            .execute()
        )
    except HttpError:
        logger.error("You're Youtube API developer key is undefined or invalid")
    else:
        for video in response["items"]:
            yield {
                "name": video["snippet"]["title"],
                "url": f"https://www.youtube.com/watch?v={video['id']['videoId']}",
            }
