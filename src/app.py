import os
import re
import sys

sys.path.append(os.path.dirname(__file__))
from SpotifyCall import compare_genres, compile_genres

import pandas as pd
import requests as http_requests
from bs4 import BeautifulSoup

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import MemoryCacheHandler
from spotipy.exceptions import SpotifyException
from flask import Flask, redirect, request, session, jsonify, render_template

app = Flask(__name__, template_folder="templates")

app.secret_key = os.getenv("FLASK_SECRET_KEY")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True

FESTIVALS_DIR = os.path.join(os.path.dirname(__file__), "festivals")


def get_auth_manager():
    return SpotifyOAuth(
        scope="user-top-read playlist-modify-public",
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        cache_handler=MemoryCacheHandler()
    )


def list_festivals():
    festivals = []
    for f in sorted(os.listdir(FESTIVALS_DIR)):
        if f.endswith(".csv"):
            slug = f[:-4]
            name = slug.replace("-", " ").replace("_", " ").title()
            try:
                df = pd.read_csv(os.path.join(FESTIVALS_DIR, f))
                count = len(df)
            except Exception:
                count = 0
            festivals.append({"slug": slug, "name": name, "count": count})
    return festivals


def parse_lineup_url(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = http_requests.get(url, timeout=10, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        artist_keywords = ["artist", "performer", "act", "lineup", "headliner", "band"]
        seen = set()
        candidates = []

        for elem in soup.find_all(True):
            classes = " ".join(elem.get("class", [])).lower()
            elem_id = elem.get("id", "").lower()
            if any(kw in classes or kw in elem_id for kw in artist_keywords):
                text = elem.get_text(strip=True)
                if text and 2 <= len(text) <= 60 and text not in seen:
                    seen.add(text)
                    candidates.append(text)

        if len(candidates) < 3:
            candidates, seen = [], set()
            for tag in soup.find_all(["h2", "h3", "h4"]):
                text = tag.get_text(strip=True)
                if text and 2 <= len(text) <= 60 and text not in seen:
                    seen.add(text)
                    candidates.append(text)

        return candidates
    except Exception:
        return []


@app.route("/")
def index():
    return render_template("index.html", festivals=list_festivals())


@app.route("/login")
def login():
    print("login:start", flush=True)
    auth_manager = get_auth_manager()
    print("login:auth_manager_created", flush=True)
    url = auth_manager.get_authorize_url()
    print("login:url_built", flush=True)
    return redirect(url)


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

    next_slug = session.pop("next", "hinterland")
    return redirect(f"/results/{next_slug}")


@app.route("/results/<festival_slug>")
def results(festival_slug):
    token = session.get("token")
    if not token:
        session["next"] = festival_slug
        return redirect("/login")

    csv_path = os.path.join(FESTIVALS_DIR, f"{festival_slug}.csv")
    if not os.path.exists(csv_path):
        return redirect("/")

    sp = spotipy.Spotify(auth=token["access_token"])
    try:
        top_artists = sp.current_user_top_artists(limit=50, time_range="medium_term")
    except SpotifyException:
        session.clear()
        session["next"] = festival_slug
        return redirect("/login")

    names = [a["name"] for a in top_artists["items"]]
    genres = compile_genres(names)

    df = pd.read_csv(csv_path)
    artist_names = df["Artist Name"].tolist()
    festival_name = festival_slug.replace("-", " ").replace("_", " ").title()

    matches = compare_genres(genres, artist_names, sp=sp)
    top_score = max(matches[0]["score"] if matches else 0, 1)
    matched_names = [m["name"] for m in matches if m["score"] > 0][:10]

    return render_template(
        "results.html",
        matches=matches,
        top_artists=names,
        top_score=top_score,
        matched_names=matched_names,
        festival_name=festival_name,
    )


@app.route("/parse", methods=["POST"])
def parse():
    url = request.form.get("url", "").strip()
    if not url:
        return redirect("/")
    artists = parse_lineup_url(url)
    return render_template("confirm.html", artists=artists, source_url=url)


@app.route("/confirm", methods=["POST"])
def confirm():
    festival_name = request.form.get("festival_name", "").strip()
    artists_raw = request.form.get("artists", "")
    artists = [a.strip() for a in artists_raw.splitlines() if a.strip()]

    if not festival_name or not artists:
        return redirect("/")

    slug = re.sub(r"[^a-z0-9]+", "-", festival_name.lower()).strip("-")
    csv_path = os.path.join(FESTIVALS_DIR, f"{slug}.csv")
    pd.DataFrame({"Artist Name": artists}).to_csv(csv_path, index=False)

    token = session.get("token")
    if not token:
        session["next"] = slug
        return redirect("/login")
    return redirect(f"/results/{slug}")


@app.route("/create_playlist", methods=["POST"])
def create_playlist():
    token = session.get("token")
    if not token:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    artist_names = data.get("artists", [])
    festival_name = data.get("festival_name", "Festival")
    if not artist_names:
        return jsonify({"error": "No artists provided"}), 400

    sp = spotipy.Spotify(auth=token["access_token"])
    try:
        playlist = sp.current_user_playlist_create(
            name=f"{festival_name} Matches",
            public=True,
            description=f"Your personalized {festival_name} lineup based on your Spotify taste"
        )

        track_uris = []
        for name in artist_names:
            track_results = sp.search(q=f"artist:{name}", type="track", limit=5)
            tracks = track_results["tracks"]["items"]
            track_uris.extend(t["uri"] for t in tracks)

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
        "festivals": list_festivals(),
        "env": {
            "FLASK_SECRET_KEY": bool(os.getenv("FLASK_SECRET_KEY")),
            "SPOTIPY_CLIENT_ID": bool(os.getenv("SPOTIPY_CLIENT_ID")),
            "SPOTIPY_CLIENT_SECRET": bool(os.getenv("SPOTIPY_CLIENT_SECRET")),
            "SPOTIPY_REDIRECT_URI": os.getenv("SPOTIPY_REDIRECT_URI"),
            "FM_API_KEY": bool(os.getenv("FM_API_KEY")),
        },
    })


if __name__ == "__main__":
    app.run(debug=True)
