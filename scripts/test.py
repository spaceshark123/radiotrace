import datetime

import requests
import re
import time
import uuid


class BroadcastifyGuestClient:
    def __init__(self):
        self.base_url = "https://www.broadcastify.com"
        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1",
            "Origin": self.base_url,
        })

    def init_playlist(self, playlist_uuid):
        print(f"[*] Fetching base console page to capture session keys...")
        url = f"{self.base_url}/calls/playlists/?uuid={playlist_uuid}&view=console"

        # The GET request captures any essential first-party cookies (like PHP session IDs)
        res = self.session.get(url)

        session_key = str(uuid.uuid4())[:13]
        pos = int(time.time())

        sk_match = re.search(
            r'var\s+sessionKey\s*=\s*[\'"]([^\'"]+)[\'"]', res.text)
        if sk_match:
            session_key = sk_match.group(1)

        pos_match = re.search(r'var\s+pos\s*=\s*(\d+)', res.text)
        if pos_match:
            pos = pos_match.group(1)

        return session_key, pos

    def get_live_calls(self, playlist_uuid, groups_string, pos, session_key, is_init=False):
        url = f"{self.base_url}/calls/apis/live-calls"

        headers = {
            "Accept": "*/*",
            "Referer": f"{self.base_url}/calls/playlists/?uuid={playlist_uuid}&view=console",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

        # Set doInit to "1" on the first run to grab recent history, "0" for subsequent polling
        payload = {
            "groups": groups_string,
            "pos": pos,
            "doInit": "1" if is_init else "0",
            "systemId": "0",
            "sid": "0",
            "playlist_uuid": playlist_uuid,
            "sessionKey": session_key,
            "capPass": ""
        }

        response = self.session.post(url, data=payload, headers=headers)

        try:
            return response.json()
        except ValueError:
            print(f"[-] JSON Decode Error. Status: {response.status_code}")
            return None


if __name__ == "__main__":
    PLAYLIST_UUID = "4c5b16b0-2974-11ef-9e04-0e98d5b32039"
    GROUPS_STRING = "8198-10020,5834-19759,5834-19753,5834-19743,5834-19741,5834-19735,5834-19727,5834-19894,5834-19314,8340-61801,5834-19390,8340-52001,8340-51101,8340-53001,5834-19435,5834-19355,5834-19334,8340-61901,5834-19875,8340-61201,8198-10190,8198-10191,8198-10270,8340-61001,8340-51001,5834-19441,5834-19439"

    client = BroadcastifyGuestClient()

    # 1. Get the initial bookmark (pos) and sessionKey from the page source
    session_key, current_pos = client.init_playlist(PLAYLIST_UUID)

    # 2. Flag to ensure we only ask for the backlog on the very first request
    is_initial_request = True

    while True:
        print(
            f"[*] Polling API (doInit={int(is_initial_request)}, pos={current_pos})...")

        # 3. Make the request using the current cursor
        data = client.get_live_calls(
            PLAYLIST_UUID, GROUPS_STRING, current_pos, session_key, is_init=is_initial_request)

        if data:
            calls = data.get('calls', [])
            print(f"[+] Found {len(calls)} new calls.")

            for call in calls:
                print(
                    f"    - TG: {call.get('tgName', 'Unknown')} | Dur: {call.get('callDuration', 0)}s")

            # 4. OVERWRITE your local cursor with the server's new cursor
            # If the server doesn't send one (e.g., error), we keep the old one to try again
            if 'lastPos' in data:
                current_pos = data['lastPos']

        # 5. Lock out the initialization flag so we only fetch NEW calls going forward
        is_initial_request = False

        # 6. Wait before polling again to avoid rate limits
        time.sleep(5)
