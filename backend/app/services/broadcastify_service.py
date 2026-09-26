"""Broadcastify live Atlanta police radio metadata and stream URL resolution."""

from __future__ import annotations

import logging
import time
from wsgiref import headers

import requests

from app.config import Config

logger = logging.getLogger(__name__)

last_current_time: int = 0

class BroadcastifyError(RuntimeError):
    """Raised when Broadcastify metadata cannot be fetched."""

# fetch list of current clips from Broadcastify (metadata only)
def get_clips(current_time: int | None = None) -> dict:
    global last_current_time

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:144.0) Gecko/20100101 Firefox/144.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            # 'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://www.broadcastify.com',
            'Sec-GPC': '1',
            'Connection': 'keep-alive',
            'Referer': 'https://www.broadcastify.com/calls/playlists/?uuid=4c5b16b0-2974-11ef-9e04-0e98d5b32039&view=console',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            # Requests doesn't support trailers
            # 'TE': 'trailers',
        }

        current_time = last_current_time if current_time is None else current_time
        if current_time == 0:
            # this is the first time fetching clips, so we need to call it twice, discarding the first response
            response = requests.post(
                'https://www.broadcastify.com/calls/apis/live-calls',
                headers=headers,
                data={
                    'groups': '8198-10020,5834-19759,5834-19753,5834-19743,5834-19741,5834-19735,5834-19727,5834-19894,5834-19314,8340-61801,5834-19390,8340-52001,8340-51101,8340-53001,5834-19435,5834-19355,5834-19334,8340-61901,5834-19875,8340-61201,8198-10190,8198-10191,8198-10270,8340-61001,8340-51001,5834-19441,5834-19439',
                    'pos': '0',
                    'doInit': '0',
                    'systemId': '0',
                    'sid': '0',
                    'playlist_uuid': '4c5b16b0-2974-11ef-9e04-0e98d5b32039',
                    'sessionKey': '8aca322c-a9a8',
                    'capPass': '',
                },
                timeout=Config.HTTP_TIMEOUT_SECONDS,
            )
            response.raise_for_status()

        data = {
            'groups': '8198-10020,5834-19759,5834-19753,5834-19743,5834-19741,5834-19735,5834-19727,5834-19894,5834-19314,8340-61801,5834-19390,8340-52001,8340-51101,8340-53001,5834-19435,5834-19355,5834-19334,8340-61901,5834-19875,8340-61201,8198-10190,8198-10191,8198-10270,8340-61001,8340-51001,5834-19441,5834-19439',
            'pos': str(current_time), # unix time
            'doInit': '0',
            'systemId': '0',
            'sid': '0',
            'playlist_uuid': '4c5b16b0-2974-11ef-9e04-0e98d5b32039',
            'sessionKey': '8aca322c-a9a8', # may need to update
            'capPass': '',
        }

        response = requests.post(
            'https://www.broadcastify.com/calls/apis/live-calls',
            headers=headers,
            data=data,
            timeout=Config.HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        # Update the last_current_time with the last_pos field from the response
        json_response = response.json()
        last_current_time = json_response.get('lastPos', last_current_time)
        # limit the number of calls returned to 5
        json_response['calls'] = json_response.get('calls', [])[:5]
        return json_response
    except requests.RequestException as exc:
        logger.error("Failed to fetch Broadcastify clips: %s", exc)
        raise BroadcastifyError("Unable to fetch Broadcastify clips") from exc

# fetch a specific clip from Broadcastify (returns raw audio)
def get_clip(clip_hash: str, system_id: str, clip_name: str, clip_encoding: "mp3" | "m4a") -> bytes:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:144.0) Gecko/20100101 Firefox/144.0',
            'Accept': 'audio/webm,audio/ogg,audio/wav,audio/*;q=0.9,application/ogg;q=0.7,video/*;q=0.6,*/*;q=0.5',
            'Accept-Language': 'en-US,en;q=0.5',
            'Range': 'bytes=0-',
            'Origin': 'https://www.broadcastify.com',
            'Connection': 'keep-alive',
            'Referer': 'https://www.broadcastify.com/',
            'Sec-Fetch-Dest': 'audio',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            # 'Accept-Encoding': 'identity',
            'Priority': 'u=4',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }

        response = requests.get(
            f'https://calls.broadcastify.com/{clip_hash}/{system_id}/{clip_name}.{clip_encoding}',
            headers=headers,
            timeout=Config.HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.content
    except requests.RequestException as exc:
        logger.error("Failed to fetch Broadcastify clip %s: %s", clip_hash, exc)
        raise BroadcastifyError(f"Unable to fetch Broadcastify clip {clip_hash}") from exc