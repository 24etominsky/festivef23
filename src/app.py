from flask import Flask, redirect, request, session, jsonify, render_template

import sys
import os
sys.path.append(os.path.dirname(__file__))
from SpotifyCall import compare_genres_to_CSV, compile_genres, get_spotify_info

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os

app = Flask(__name__, template_folder="templates")

app.secret_key = os.getenv("FLASK_SECRET_KEY")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True

SCOPE = "user-top-read playlist-modify-private"

def get_auth_manager(cache_handler=None):
    return SpotifyOAuth(
        scope=SCOPE,
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        cache_handler=cache_handler
    )

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login():
    auth_manager = get_auth_manager()
    return redirect(auth_manager.get_authorize_url())


@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return redirect("/")

    auth_manager = get_auth_manager()
    try:
        token = auth_manager.get_access_token(code, as_dict=True)
        session["token"] = token
    except Exception as e:
        print(f"Auth error: {e}")
        return redirect("/")

    return redirect("/results")

@app.route("/results")
def results():
    token = session.get("token")
    if not token:
        return redirect("/login")

    sp = spotipy.Spotify(auth=token["access_token"])
    top_artists = sp.current_user_top_artists(limit=50, time_range="medium_term")
    names = [a["name"] for a in top_artists["items"]]
    genres = compile_genres(names)
    matches = compare_genres_to_CSV(genres, sp=sp)

    top_score = matches[0]["score"] if matches else 1

    # Store top 10 matched artist names for playlist creation
    session["top_artist_names"] = [
        m["name"] for m in matches[:10] if m["score"] > 0
    ]

    return render_template("results.html", matches=matches, top_artists=names, top_score=top_score)

@app.route("/create-playlist", methods=["POST"])
def create_playlist():
    token = session.get("token")
    if not token:
        return jsonify({"error": "not authenticated"}), 401

    artist_names = session.get("top_artist_names", [])
    if not artist_names:
        return jsonify({"error": "no artists found — try reloading your results first"}), 400

    sp = spotipy.Spotify(auth=token["access_token"])

    track_uris = []
    for name in artist_names:
        try:
            result = sp.search(q=f'artist:"{name}"', type="artist", limit=1)
            items = result["artists"]["items"]
            if not items or items[0]["name"].lower() != name.lower():
                continue
            artist_id = items[0]["id"]
            tracks = sp.artist_top_tracks(artist_id)["tracks"][:5]
            track_uris.extend([t["uri"] for t in tracks])
        except Exception as e:
            print(f"Error fetching tracks for {name}: {e}")
            continue

    if not track_uris:
        return jsonify({"error": "Could not fetch tracks — no matched artists had a Spotify profile."}), 500

    try:
        user_id = sp.current_user()["id"]
        playlist = sp.user_playlist_create(
            user_id,
            "Festival Picks",
            public=False,
            description="Top tracks from your Hinterland matches — made by Festival Match"
        )
        sp.playlist_add_items(playlist["id"], track_uris)
    except Exception as e:
        print(f"Playlist creation error: {e}")
        return jsonify({"error": "Spotify rejected the request — try logging out and back in to grant playlist permissions."}), 500

    return jsonify({"playlist_url": playlist["external_urls"]["spotify"]})

@app.route("/debug")
def debug():
    return jsonify({
        "cwd": os.getcwd(),
        "file": __file__,
        "template_folder": app.template_folder,
        "files": os.listdir(os.getcwd())
    })

if __name__ == "__main__":
    app.run(debug=True)
