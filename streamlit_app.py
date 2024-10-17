import streamlit as st
from pydub import AudioSegment
from io import BytesIO

# Title of the app
st.title("🎵 Audio Crossfade Mixer")

# Description of the app
st.write("Upload two audio files and we'll mix them using a crossfade effect.")

# Function to crossfade two audio files
def crossfade_audio(file1, file2, fade_duration=5000):
    # Load the first 10 seconds of each audio file
    audio1 = AudioSegment.from_file(file1)[:10000]  # First 10 seconds of audio1
    audio2 = AudioSegment.from_file(file2)[:10000]  # First 10 seconds of audio2
    
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

# Upload audio files
audio_file1 = st.file_uploader("Upload First Audio File", type=["mp3", "wav", "ogg", "flac"])
audio_file2 = st.file_uploader("Upload Second Audio File", type=["mp3", "wav", "ogg", "flac"])

# Process and mix the audio files if both are uploaded
if audio_file1 and audio_file2:
    st.write("Mixing the audio files...")

    # Mix the audio files with crossfade
    mixed_audio = crossfade_audio(audio_file1, audio_file2)

    # Play the mixed audio file
    st.audio(mixed_audio, format="audio/mp3")

    # Option to download the mixed audio
    st.download_button("Download Mixed Audio", mixed_audio, file_name="crossfaded_audio.mp3")
