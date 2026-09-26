import requests
import re
import time
import uuid
import os
import pygame


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

        # Sagalee taphachiisuuf pygame jalqabsiisi
        pygame.mixer.init()

    def init_playlist(self, playlist_uuid):
        print(f"[*] Fetching base console page to capture session keys...")
        url = f"{self.base_url}/calls/playlists/?uuid={playlist_uuid}&view=console"

        res = self.session.get(url)

        session_key = str(uuid.uuid4())[:13]
        pos = 0

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

    def download_and_play(self, call):
        """
        Sagalee (audio) buufatee erga taphachiisee booda faayilicha haqa.
        """
        audio_url = f"https://calls.broadcastify.com/{call['hash']}/{call['systemId']}/{call['filename']}.{call['enc']}"
        file_path = f"{call['filename']}.{call['enc']}"

        print(f"    [*] Fetching audio: {call['filename']}.{call['enc']}")

        try:
            res = requests.get(audio_url)
            if res.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(res.content)

                print(
                    f"    [>] Playing: {call.get('display', 'Unknown TG')} - {call.get('descr', '')}")

                # Sagalee pygame fayyadamuun taphachiisi
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()

                # Hanga sagaleen xumuramutti eegi
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)

                # Faayilicha gadi lakkisi (unload)
                pygame.mixer.music.unload()

                # Faayilicha haqii bakka qulqulleessi
                os.remove(file_path)
            else:
                print(
                    f"    [-] Failed to download audio. HTTP {res.status_code}")
        except Exception as e:
            print(f"    [-] Error processing audio: {e}")

            # Yoo dogoggorri uumame faayilicha haquu mirkaneessi
            if os.path.exists(file_path):
                try:
                    pygame.mixer.music.unload()
                    os.remove(file_path)
                except:
                    pass


if __name__ == "__main__":
    PLAYLIST_UUID = "4c5b16b0-2974-11ef-9e04-0e98d5b32039"
    GROUPS_STRING = "8198-10020,5834-19759,5834-19753,5834-19743,5834-19741,5834-19735,5834-19727,5834-19894,5834-19314,8340-61801,5834-19390,8340-52001,8340-51101,8340-53001,5834-19435,5834-19355,5834-19334,8340-61901,5834-19875,8340-61201,8198-10190,8198-10191,8198-10270,8340-61001,8340-51001,5834-19441,5834-19439"

    client = BroadcastifyGuestClient()
    session_key, current_pos = client.init_playlist(PLAYLIST_UUID)

    is_initial_request = True

    print("[*] Starting real-time listener...")
    while True:
        data = client.get_live_calls(
            PLAYLIST_UUID, GROUPS_STRING, current_pos, session_key, is_init=is_initial_request)

        if data:
            calls = data.get('calls', [])

            # Yeroo jalqabaa waamicha durii dhiisuun gara waamicha haaraatti ce'i
            if is_initial_request:
                print(
                    f"[*] Ignored {len(calls)} historical calls. Synced to live edge.")
            elif calls:
                print(f"\n[+] Found {len(calls)} new calls.")
                for call in calls:
                    client.download_and_play(call)

            # 'lastPos' isa haaraa fudhu
            if 'lastPos' in data:
                current_pos = data['lastPos']

        is_initial_request = False

        time.sleep(5)
