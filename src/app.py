from flask import Flask, redirect, request, session, jsonify, render_template

import sys
import os
sys.path.append(os.path.dirname(__file__))
from SpotifyCall import compare_genres_to_CSV, compile_genres, get_spotify_url

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os

app = Flask(__name__, template_folder="templates")

app.secret_key = os.getenv("FLASK_SECRET_KEY")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True

def get_auth_manager(cache_handler=None):
    return SpotifyOAuth(
        scope="user-top-read playlist-modify-public user-read-private",
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
        session["token"] = token  # stored per-user session
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

    return render_template("results.html", matches=matches, top_artists=names, top_score=top_score)

@app.route("/create_playlist", methods=["POST"])
def create_playlist():
    token = session.get("token")
    if not token:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    artist_names = data.get("artists", [])
    if not artist_names:
        return jsonify({"error": "No artists provided"}), 400

    sp = spotipy.Spotify(auth=token["access_token"])
    try:
        user_id = sp.current_user()["id"]
        playlist = sp.user_playlist_create(
            user=user_id,
            name="Hinterland Festival Matches",
            public=True,
            description="Your personalized Hinterland lineup based on your Spotify taste"
        )

        track_uris = []
        for name in artist_names:
            results = sp.search(q=f"artist:{name}", type="artist", limit=1)
            artists = results["artists"]["items"]
            if artists:
                artist_id = artists[0]["id"]
                top_tracks = sp.artist_top_tracks(artist_id)
                if top_tracks["tracks"]:
                    track_uris.append(top_tracks["tracks"][0]["uri"])

        if track_uris:
            sp.playlist_add_items(playlist["id"], track_uris)

        return jsonify({"url": playlist["external_urls"]["spotify"]})
    except Exception as e:
        print(f"Playlist error: {e}")
        return jsonify({"error": str(e)}), 500

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