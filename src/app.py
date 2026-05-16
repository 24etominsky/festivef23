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
    matches, genre_matches = compare_genres_to_CSV(genres)

    # Convert "Artist:score" strings to a list of dicts and sort
    parsed = [{"name": m.split(":")[0], "score": int(m.split(":")[1])} for m in matches]
    parsed.sort(key=lambda x: x["score"], reverse=True)

    return render_template("results.html", matches=parsed, top_artists=names)

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