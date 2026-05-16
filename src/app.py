from flask import Flask, redirect, request, session, jsonify, render_template

import sys
import os
sys.path.append(os.path.dirname(__file__))
from SpotifyCall import compare_genres_to_CSV, compile_genres

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os

app = Flask(__name__, template_folder="templates")

app.secret_key = os.getenv("FLASK_SECRET_KEY")

def get_auth_manager(cache_handler=None):
    return SpotifyOAuth(
        scope="user-top-read",
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
    auth_manager = get_auth_manager()
    token = auth_manager.get_access_token(code)
    session["token"] = token
    return redirect("/results")

@app.route("/results")
def results():
    token = session.get("token")
    if not token:
        return redirect("/login")

    sp = spotipy.Spotify(auth=token["access_token"])
    top_artists = sp.current_user_top_artists(limit=5, time_range="medium_term")
    names = [a["name"] for a in top_artists["items"]]
    genres = compile_genres(names)
    matches, genre_matches = compare_genres_to_CSV(genres)

    return jsonify({"matches": matches, "genreMatches": genre_matches})

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