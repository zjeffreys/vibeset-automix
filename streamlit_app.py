import streamlit as st
import yt_dlp
import os
import tempfile
from pydub import AudioSegment
import requests

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
    return response.json().get('items', [])

# Streamlit UI setup
st.title("YouTube Audio Mixer")

# Upload cookie file
cookie_file = st.file_uploader("Upload YouTube cookies file (optional):", type=["txt"])

# Input fields for song names
song_name1 = st.text_input("Enter the first song name:")
song_name2 = st.text_input("Enter the second song name:")

# Display dropdowns for search results
video_url1 = ""
video_url2 = ""

if song_name1:
    search_results1 = search_youtube(song_name1)
    options1 = [f"{video['snippet']['title']} - {video['snippet']['channelTitle']}" for video in search_results1]
    selected_video1 = st.selectbox("Select the first song:", options1)
    if selected_video1:
        video_url1 = f"https://www.youtube.com/watch?v={search_results1[options1.index(selected_video1)]['id']['videoId']}"

if song_name2:
    search_results2 = search_youtube(song_name2)
    options2 = [f"{video['snippet']['title']} - {video['snippet']['channelTitle']}" for video in search_results2]
    selected_video2 = st.selectbox("Select the second song:", options2)
    if selected_video2:
        video_url2 = f"https://www.youtube.com/watch?v={search_results2[options2.index(selected_video2)]['id']['videoId']}"

# Helper function to download audio using yt-dlp
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

# Mix button
if st.button("Mix Audio"):
    if video_url1 and video_url2:
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save the uploaded cookie file temporarily if provided
                cookie_path = None
                if cookie_file:
                    cookie_path = os.path.join(temp_dir, "cookies.txt")
                    with open(cookie_path, "wb") as f:
                        f.write(cookie_file.read())

                audio_file1 = download_audio_yt_dlp(video_url1, temp_dir, "audio1", cookie_path)
                audio_file2 = download_audio_yt_dlp(video_url2, temp_dir, "audio2", cookie_path)

                if not audio_file1 or not audio_file2:
                    st.error("Failed to download audio from one or both videos.")
                else:
                    audio1 = AudioSegment.from_file(audio_file1)
                    audio2 = AudioSegment.from_file(audio_file2)

                    mixed_audio = audio1.overlay(audio2)
                    mixed_file_path = os.path.join(temp_dir, "mixed_audio.mp3")
                    mixed_audio.export(mixed_file_path, format="mp3")

                    st.subheader("Original Audios")
                    st.audio(audio_file1, format="audio/mp3")
                    st.audio(audio_file2, format="audio/mp3")

                    st.subheader("Mixed Audio")
                    st.audio(mixed_file_path, format="audio/mp3")

        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter both song names and select the corresponding videos.")