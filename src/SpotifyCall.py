import json
import os
from dotenv import load_dotenv
import spotipy
import pandas as pd
from spotipy.oauth2 import SpotifyOAuth
import requests

load_dotenv()


sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="user-top-read"))

def get_genres_lastfm(artist_name, api_key):
    url = "https://ws.audioscrobbler.com/2.0/"
    params = {
        "method": "artist.getTopTags",
        "artist": artist_name,
        "api_key": api_key,
        "format": "json"
    }
    res = requests.get(url, params=params).json()
    tags = [t["name"] for t in res.get("toptags", {}).get("tag", [])]
    return tags[:5]  # top 5 tags

def compile_genres(list_of_artists):
    key = os.getenv("FM_API_KEY")
    genresList = []
    for artist in list_of_artists:
        genres = get_genres_lastfm(artist, key)
        # print(genres)
        genresList.extend(genres)
        # print(genresList)
    return genresList

def get_users_top_genres():
    top_artists = sp.current_user_top_artists(limit=50, time_range="short_term")
    # print(json.dumps(top_artists, indent=4))
    names = set()
    for artist in top_artists['items']:
        name = artist['name']
        names.add(name)
    genres = compile_genres(names)
    return genres
    # print(genres)
    # print(len(genres))

def compare_genres_to_CSV(genres):
    matches = []
    genreMatches = []
    fm_key = os.getenv("FM_API_KEY")
    df = pd.read_csv("../festival_lineup.csv")
    artist_names = df["Artist Name"].tolist()
    for artist in artist_names:
        counter = 0
        # print(artist)
        genresNew = get_genres_lastfm(artist, fm_key)
        # print(genresNew)
        for genre in genresNew:
            if genre in genres:
                # print("Match!!")
                counter += genres.count(genre)
                genreMatches.append(genre)
        matches.append(artist + ":" + str(counter))
    return (matches, genreMatches)

def sort_results(matches):
    for pos in range(len(matches)):
        for potential in range(pos,len(matches)):
            if int(matches[pos].split(":")[1]) < int(matches[potential].split(":")[1]):
                temp = matches[pos]
                matches[pos] = matches[potential]
                matches[potential] = temp
    return matches

def make_dict(genres):
    dict = {}
    for genre in genres:
        if genre in dict:
            dict[genre] += 1
        else:
            dict[genre] = 1
    return dict

genres = get_users_top_genres()
genres.sort()
print(make_dict(genres))
print(len(genres))
matches = compare_genres_to_CSV(genres)
# matches = ['KATSEYE:3', 'beabadoobee:3', 'ASHNIKKO:5', 'AUDREY NUNA:5', 'Oklou:2', 'Jane Remover:2', 'Frost Children:3', 'Porch Light:1', 'Nourished by Time:1', 'Pixel Grip:2', 'Lorde:4', 'MUNA:4', 'Snow Strippers:2', 'Paris Paloma:4', 'SOFIA ISELLA:5', 'Wisp:2', 'Saint Avangeline:2', 'Between Friends:4', 'Ninajirachi:3', 'Mumford & Sons:3', 'Jessie Murph:2', 'The Format:5', 'Santigold:4', 'CMAT:3', 'Julia Wolf:5', 'Waylon Wyatt:1', 'Amble:2', 'The Brook & The Bluff:2', 'Buffalo Traffic Jam:2', 'Kali Uchis:2', 'Young Miko:3', 'Geese:2', 'Wet Leg:4', 'Suki Waterhouse:5', 'Audrey Hobert:4', 'Samia:5', 'Haute & Freddy:2', 'Die Spitz:0', 'Gouge Away:2']
sorted = sort_results(matches[0])
print(sorted)
# print(matches[0])
# print(matches[1])




