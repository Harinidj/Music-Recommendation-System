import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Load environment variables from .env
load_dotenv()

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py', silent=True)
app.config['SECRET_KEY'] = app.config.get('SECRET_KEY', 'ea6e57ca01737bc85c0deb1e463a541b')

users = {
    'mita': {'password': 'mypass', 'favorites': []},
    'john': {'password': 'mypass', 'favorites': []},
    'alia': {'password': 'mypass', 'favorites': []}
}

client_credentials_manager = SpotifyClientCredentials()
sp = spotipy.Spotify(auth_manager=client_credentials_manager)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        if username in users:
            flash('Username already exists, babe.', 'error')
        else:
            # Initialize the user with favorites and playlists
            users[username] = {'password': password, 'favorites': [], 'playlists': []}
            flash('Registration successful! Now log in, sweetie.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        stored_password = users.get(username, {}).get('password')
        if stored_password and check_password_hash(stored_password, password):
            session['username'] = username
            flash('Logged in successfully, sweetie!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials, babe. Try again.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully, sugar.', 'success')
    return redirect(url_for('login'))


@app.route('/create_playlist', methods=['POST'])
def create_playlist():
    if 'username' not in session:
        flash("Please log in to create a playlist, babe.", "error")
        return redirect(url_for('login'))
    playlist_name = request.form.get("playlist_name")
    if not playlist_name:
        flash("Playlist name cannot be empty, sweetie.", "error")
        return redirect(url_for('home'))

    # Append a new playlist (with a name and empty tracks list)
    user = session['username']
    users[user]['playlists'].append({'name': playlist_name, 'tracks': []})
    flash(f"Playlist '{playlist_name}' created, babe!", "success")
    return redirect(url_for('home'))


@app.route('/')
def home():
    tracks = []
    # If user is logged in and has favorites, generate recommendations
    if 'username' in session and users[session['username']].get('favorites'):
        seed_tracks = users[session['username']]['favorites'][:5]  # use up to 5 seeds
        try:
            recs = sp.recommendations(seed_tracks=seed_tracks, limit=10)
            tracks = recs['tracks']
        except Exception as e:
            flash("Error generating recommendations. Showing new releases instead.", "error")
    else:
        # Otherwise show new releases
        new_releases = sp.new_releases(country='US', limit=10)
        albums = new_releases['albums']['items']
        for album in albums:
            album_tracks = sp.album_tracks(album['id'])['items']
            if album_tracks:
                track = album_tracks[0]
                # Add album info so we can display album art
                track['album'] = album
                tracks.append(track)

    # If the user is logged in, get their playlists
    user_playlists = []
    if 'username' in session:
        user_playlists = users[session['username']].get('playlists', [])

    return render_template('home.html', tracks=tracks, playlists=user_playlists)


MOOD_MAPPING = {
    'happy': 'happy upbeat',
    'sad': 'melancholy',
    'energetic': 'energetic workout',
    'calm': 'calm instrumental'
}


@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'username' not in session:
        flash("You need to log in first, babe.", "error")
        return redirect(url_for('login'))
    username = session['username']
    mood = request.args.get('mood', None)
    q = request.args.get('q', None)
    # Prioritize mood-based search if mood is selected
    if mood in MOOD_MAPPING:
        query = MOOD_MAPPING[mood]
    elif q:
        query = q
    else:
        # Default query if nothing is provided
        query = 'popular'

    results = sp.search(q=query, type='track', limit=10)
    tracks = results['tracks']['items']
    return render_template('dashboard.html', username=username, tracks=tracks, selected_mood=mood)


@app.route('/add_favorite', methods=['POST'])
def add_favorite():
    if 'username' not in session:
        flash("Please log in to add favorites, babe.", "error")
        return redirect(url_for('login'))
    track_id = request.form.get('track_id')
    if not track_id:
        flash("No track selected.", "error")
        return redirect(request.referrer)
    favs = users[session['username']].get('favorites', [])
    if track_id not in favs:
        favs.append(track_id)
        users[session['username']]['favorites'] = favs
        flash("Added to your favorites, sweetie!", "success")
    else:
        flash("Already in your favorites, babe.", "info")
    return redirect(request.referrer)


@app.route('/favorites')
def favorites():
    if 'username' not in session:
        flash("Please log in, sugar.", "error")
        return redirect(url_for('login'))
    favorite_ids = users[session['username']].get('favorites', [])
    fav_tracks = []
    for tid in favorite_ids:
        try:
            track = sp.track(tid)
            fav_tracks.append(track)
        except Exception as e:
            continue
    return render_template('favorites.html', tracks=fav_tracks)

if __name__ == '__main__':
    app.run(debug=True)
