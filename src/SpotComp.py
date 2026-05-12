import json
import os
from dotenv import load_dotenv
import spotipy
import pandas as pd
from spotipy.oauth2 import SpotifyOAuth
import requests

load_dotenv()
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="user-top-read"))

print("im running")
play_lists = sp.current_user_playlists("bhnapu8y31mues7cljccrl5hp")
print(json.dumps(play_lists, indent=4))
# print(type(user['tracks']['items'][0]))
# print(user['tracks']['items'])
# print(json.dumps(user['tracks']['items'], indent=4))