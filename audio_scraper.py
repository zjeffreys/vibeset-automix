import streamlit as st
from pytube import YouTube
import os

# Title and description
st.title("YouTube Audio Downloader")
st.write("Enter a YouTube video URL to download the audio and listen to it. Need to download chrome extension for this.")

# Input for YouTube URL
video_url = st.text_input("Enter YouTube Video URL:")

if video_url:
    try:
        # Attempt to fetch YouTube object
        st.write("Validating YouTube URL...")
        yt = YouTube(video_url)
        st.write(f"Video Title: {yt.title}")
        st.write(f"Channel: {yt.author}")
        st.write(f"Views: {yt.views:,}")
        
        # Select the best audio stream
        audio_stream = yt.streams.filter(only_audio=True).first()
        
        if audio_stream:
            st.write(f"Audio stream found: {audio_stream.mime_type}, {audio_stream.abr}")
            st.write("Starting download...")
            
            # Download the audio
            audio_file = audio_stream.download(output_path=".")
            base, ext = os.path.splitext(audio_file)
            new_file = base + '.mp3'
            os.rename(audio_file, new_file)
            
            # Provide download link
            with open(new_file, "rb") as file:
                st.audio(file.read(), format='audio/mp3')
                st.download_button(
                    label="Download Audio",
                    data=file,
                    file_name=os.path.basename(new_file),
                    mime="audio/mp3"
                )
            st.success("Audio downloaded successfully!")
        else:
            st.error("No audio stream available. The video might have restrictions or no audio tracks.")

    except Exception as e:
        # More descriptive error handling
        if "403" in str(e):
            st.error("HTTP Error 403: YouTube might be blocking access to this video. This could be due to regional restrictions, private video settings, or changes in YouTube's API.")
        elif "RegexMatchError" in str(e):
            st.error("Invalid YouTube URL. Please make sure the link is correct.")
        elif "VideoUnavailable" in str(e):
            st.error("The video is unavailable. This could be due to copyright restrictions or other issues.")
        else:
            st.error(f"An unexpected error occurred: {e}")
