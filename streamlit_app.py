import streamlit as st
import yt_dlp
import os
import tempfile
from pydub import AudioSegment
import requests
import time
import numpy as np
import matplotlib.pyplot as plt
import librosa

# YouTube Data API key from Streamlit secrets
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]

# Function to search YouTube using YouTube Data API
def search_youtube(query):
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'maxResults': 5,
        'key': YOUTUBE_API_KEY
    }
    response = requests.get(url, params=params)
    json_data = response.json()
    if "error" in json_data:
        # Log the error message.
        st.error("YouTube Data API error: " + json_data["error"]["message"])
        return []
    return json_data.get('items', [])

# Function to check validity of the uploaded cookie file.
# Assumes a Netscape cookie file format:
# Each non-comment line should have at least 7 whitespace‐separated fields:
#   domain, flag, path, secure, expiration, name, value
def check_cookie_file_validity(cookie_bytes):
    try:
        cookie_str = cookie_bytes.decode("utf-8")
    except Exception as e:
        st.error("Failed to decode cookie file: " + str(e))
        return False

    now = time.time()
    found_youtube_cookie = False
    for line in cookie_str.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue  # skip headers/comments
        parts = line.split()
        if len(parts) < 7:
            continue  # skip invalid lines
        domain = parts[0]
        # Check only cookies for youtube.com
        if "youtube.com" in domain:
            found_youtube_cookie = True
            try:
                expiration = int(parts[4])
            except ValueError:
                continue
            # If the cookie has a nonzero expiration and it’s already expired, the cookie is outdated.
            if expiration != 0 and expiration < now:
                return False
    # If no YouTube cookie was found at all, consider the file invalid.
    if not found_youtube_cookie:
        return False
    return True

# Helper function to compute loudness envelope
def get_loudness_envelope(audio, frame_duration_ms=100):
    times = []
    loudness = []
    for ms in range(0, len(audio), frame_duration_ms):
        segment = audio[ms:ms+frame_duration_ms]
        # dBFS can be -inf for absolute silence; replace it with a very low number
        dB = segment.dBFS if segment.dBFS != float("-inf") else -100
        times.append(ms / 1000.0)
        loudness.append(dB)
    return times, loudness

# Helper function to compute BPM estimates over time using librosa.
def get_bpm_over_time(audio):
    # Convert AudioSegment to a numpy array of samples.
    samples = np.array(audio.get_array_of_samples())
    sr = audio.frame_rate
    # If stereo, average the channels.
    if audio.channels > 1:
        samples = samples.reshape((-1, audio.channels))
        samples = np.mean(samples, axis=1)
    samples = samples.astype(float)
    # Compute an onset envelope.
    onset_env = librosa.onset.onset_strength(y=samples, sr=sr)
    # Get beat frames using librosa's beat tracking.
    tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    bpms = []
    times = []
    # Compute an instantaneous BPM estimate based on the interval between successive beats.
    for i in range(1, len(beat_times)):
        interval = beat_times[i] - beat_times[i-1]
        bpm = 60.0 / interval if interval > 0 else 0
        times.append((beat_times[i] + beat_times[i-1]) / 2.0)
        bpms.append(bpm)
    return times, bpms

# Helper functions to trim silence.
def trim_leading_silence(sound, silence_thresh=-50.0, chunk_size=10):
    """Removes silence from the beginning of an AudioSegment."""
    trim_ms = 0
    while trim_ms < len(sound) and sound[trim_ms:trim_ms+chunk_size].dBFS < silence_thresh:
        trim_ms += chunk_size
    return sound[trim_ms:]

def trim_trailing_silence(sound, silence_thresh=-50.0, chunk_size=10):
    """Removes silence from the end of an AudioSegment."""
    reversed_sound = sound.reverse()
    trimmed_reversed = trim_leading_silence(reversed_sound, silence_thresh, chunk_size)
    return trimmed_reversed.reverse()

# ------------------------------
# SYSTEM CHECK (runs before any song input)
# ------------------------------

st.title("YouTube Audio Mixer")
st.subheader("System Check")

# Enforce cookie file upload (no longer optional)
cookie_file = st.file_uploader("Upload YouTube cookies file (use extension):", type=["txt"])
if not cookie_file:
    st.error("A valid YouTube cookies file must be uploaded to proceed.")
    st.stop()

# Get the bytes of the cookie file once and store them.
cookie_data = cookie_file.getvalue()

# Check that the cookie file is valid.
if not check_cookie_file_validity(cookie_data):
    st.error("Cookie file is outdated or invalid. Please upload a new one.")
    st.stop()

# Test the YouTube Data API with a simple query.
test_results = search_youtube("YouTube")
# If no results are returned, assume we hit our quota (or another error occurred)
if not test_results:
    use_direct_link = True
    st.warning("YouTube Data API quota has been exceeded so can't do song-url lookup. For now, please provide direct YouTube URLs.")
else:
    use_direct_link = False
    st.success("System Check Passed: YouTube Data API and cookie file are working correctly.")

# ------------------------------
# USER INPUT (after the system check passes)
# ------------------------------

if use_direct_link:
    video_url1 = st.text_input("Enter the direct YouTube URL for the first song:")
    video_url2 = st.text_input("Enter the direct YouTube URL for the second song:")
else:
    # Input fields for song names.
    song_name1 = st.text_input("Enter the first song name:")
    song_name2 = st.text_input("Enter the second song name:")

    video_url1 = ""
    video_url2 = ""

    if song_name1:
        search_results1 = search_youtube(song_name1)
        options1 = [f"{video['snippet']['title']} - {video['snippet']['channelTitle']}" for video in search_results1]
        selected_video1 = st.selectbox("Select the first song:", options1)
        if selected_video1:
            index = options1.index(selected_video1)
            video_url1 = f"https://www.youtube.com/watch?v={search_results1[index]['id']['videoId']}"

    if song_name2:
        search_results2 = search_youtube(song_name2)
        options2 = [f"{video['snippet']['title']} - {video['snippet']['channelTitle']}" for video in search_results2]
        selected_video2 = st.selectbox("Select the second song:", options2)
        if selected_video2:
            index = options2.index(selected_video2)
            video_url2 = f"https://www.youtube.com/watch?v={search_results2[index]['id']['videoId']}"

# Helper function to download audio using yt-dlp.
def download_audio_yt_dlp(video_url, output_dir, filename, cookie_path=None):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_dir, filename),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        }
        if cookie_path:
            ydl_opts['cookiefile'] = cookie_path

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return os.path.join(output_dir, filename + ".mp3")
    except Exception as e:
        st.error(f"yt-dlp failed to download audio: {e}")
        return None

# ------------------------------
# AUDIO MIXING AND VISUALIZATION (30s Segments with Trimmed Silence)
# ------------------------------
if st.button("Mix Audio"):
    if video_url1 and video_url2:
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save the uploaded cookie file temporarily.
                cookie_path = os.path.join(temp_dir, "cookies.txt")
                with open(cookie_path, "wb") as f:
                    f.write(cookie_data)

                audio_file1 = download_audio_yt_dlp(video_url1, temp_dir, "audio1", cookie_path)
                audio_file2 = download_audio_yt_dlp(video_url2, temp_dir, "audio2", cookie_path)

                if not audio_file1 or not audio_file2:
                    st.error("Failed to download audio from one or both videos.")
                else:
                    # Load the full audio files using pydub.
                    audio1 = AudioSegment.from_file(audio_file1)
                    audio2 = AudioSegment.from_file(audio_file2)

                    # ---- Slice the Audio Segments ----
                    slice_duration = 30000  # 30 seconds in milliseconds
                    if len(audio1) < slice_duration or len(audio2) < slice_duration:
                        st.error("One of the songs is too short for the requested slicing.")
                        st.stop()

                    # Extract the last 30 seconds of song1 and the first 30 seconds of song2.
                    segment1 = audio1[-slice_duration:]
                    segment2 = audio2[:slice_duration]

                    # ---- Trim Silence ----
                    # Remove any trailing silence from segment1 and any leading silence from segment2.
                    segment1 = trim_trailing_silence(segment1, silence_thresh=-50, chunk_size=10)
                    segment2 = trim_leading_silence(segment2, silence_thresh=-50, chunk_size=10)

                    # ---- Crossfade Mixing ----
                    # Set crossfade duration (e.g., 5 seconds).
                    crossfade_duration = 5000  # 5 seconds in milliseconds
                    mixed_audio = segment1.append(segment2, crossfade=crossfade_duration)

                    # Export the mixed audio.
                    mixed_file_path = os.path.join(temp_dir, "mixed_audio.mp3")
                    mixed_audio.export(mixed_file_path, format="mp3")

                    st.subheader("Mixed Audio (Trimmed Overlap with Crossfade)")
                    st.audio(mixed_file_path, format="audio/mp3")

                    # ---- Visualization ----
                    # For visualization, we shift the timeline of segment2 by the overlap offset.
                    offset = (len(segment1) - crossfade_duration) / 1000.0

                    # Loudness graph.
                    times1, loud1 = get_loudness_envelope(segment1)
                    times2, loud2 = get_loudness_envelope(segment2)
                    times2_shifted = [t + offset for t in times2]

                    fig, ax = plt.subplots(figsize=(10, 4))
                    ax.plot(times1, loud1, label="Song 1 Loudness")
                    ax.plot(times2_shifted, loud2, label="Song 2 Loudness")
                    ax.set_xlabel("Time (s)")
                    ax.set_ylabel("Loudness (dBFS)")
                    ax.set_title("Loudness Overlap (Trimmed Segments with Overlap)")
                    ax.legend()
                    st.pyplot(fig)

                    # BPM graph.
                    times_bpm1, bpms1 = get_bpm_over_time(segment1)
                    times_bpm2, bpms2 = get_bpm_over_time(segment2)
                    times_bpm2_shifted = [t + offset for t in times_bpm2]

                    fig2, ax2 = plt.subplots(figsize=(10, 4))
                    ax2.plot(times_bpm1, bpms1, marker='o', linestyle='-', label="Song 1 BPM")
                    ax2.plot(times_bpm2_shifted, bpms2, marker='o', linestyle='-', label="Song 2 BPM")
                    ax2.set_xlabel("Time (s)")
                    ax2.set_ylabel("BPM")
                    ax2.set_title("BPM Overlap (Trimmed Segments with Overlap)")
                    ax2.legend()
                    st.pyplot(fig2)

        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter both song names (or direct URLs) and select the corresponding videos.")
