import streamlit as st
import yt_dlp

def download_audio(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info).replace(".webm", ".mp3")

st.title("YouTube Audio Downloader")
video_url = st.text_input("Enter YouTube Video URL:")

if st.button("Download"):
    try:
        file_path = download_audio(video_url)
        st.success(f"Audio downloaded successfully: {file_path}")

        with open(file_path, "rb") as file:
            st.audio(file.read(), format='audio/mp3')
            st.download_button(
                label="Download Audio",
                data=file,
                file_name=file_path.split('/')[-1],
                mime="audio/mp3",
            )
    except Exception as e:
        st.error(f"An error occurred: {e}")
