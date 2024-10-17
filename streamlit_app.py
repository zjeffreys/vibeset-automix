import streamlit as st
from pydub import AudioSegment
from io import BytesIO
import requests

# Title of the app
st.title("🎵 Audio Crossfade Mixer")

# Description of the app
st.write("Select two demo tracks, and we'll mix them using a crossfade effect.")

# Function to load audio from a public URL
def load_audio_from_url(url):
    audio_data = requests.get(url).content
    return AudioSegment.from_file(BytesIO(audio_data), format="mp3")

# Public demo track URLs from Supabase
demo_tracks = {
    "Boom Bap Flick - Quincas Moreira": "https://eexoqhyrxkhxjvgdbycw.supabase.co/storage/v1/object/public/demo_tracks/Boom_Bap_Flick_Quincas_Moreira_compressed.mp3",
    "ILY Baby - Dyalla": "https://eexoqhyrxkhxjvgdbycw.supabase.co/storage/v1/object/public/demo_tracks/ILY_Baby_Dyalla_compressed.mp3"
}

# Function to load audio from a demo track
def load_audio(selection):
    return load_audio_from_url(demo_tracks[selection])

# Function to crossfade two audio files
def crossfade_audio(file1, file2, fade_duration=5000):
    # Load the first 10 seconds of each audio file
    audio1 = file1[:10000]  # First 10 seconds of audio1
    audio2 = file2[:10000]  # First 10 seconds of audio2
    
    # Fade out audio1 over the last 5 seconds
    audio1_faded = audio1.fade_out(fade_duration)

    # Fade in audio2 over the first 5 seconds
    audio2_faded = audio2.fade_in(fade_duration)

    # Combine them together with a crossfade (audio1 fades out while audio2 fades in)
    final_audio = audio1_faded.append(audio2_faded, crossfade=fade_duration)

    # Export the mixed audio to a BytesIO object
    output = BytesIO()
    final_audio.export(output, format="mp3")
    output.seek(0)
    return output

# Select the first track
st.write("### First Audio Track")
selection1 = st.selectbox("Choose the first audio track", list(demo_tracks.keys()))

# Select the second track
st.write("### Second Audio Track")
selection2 = st.selectbox("Choose the second audio track", list(demo_tracks.keys()))

# Load the selected demo tracks
audio1 = load_audio(selection1)
audio2 = load_audio(selection2)

# Process and mix the audio files if both tracks are selected
if audio1 and audio2:
    st.write("Mixing the audio tracks...")

    # Mix the audio tracks with crossfade
    mixed_audio = crossfade_audio(audio1, audio2)

    # Play the mixed audio file
    st.audio(mixed_audio, format="audio/mp3")

    # Option to download the mixed audio
    st.download_button("Download Mixed Audio", mixed_audio, file_name="crossfaded_audio.mp3")
