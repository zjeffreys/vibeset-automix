import streamlit as st
from pydub import AudioSegment
from io import BytesIO
import requests
import librosa
import soundfile as sf  # Import soundfile for writing WAV files
import numpy as np  # Import NumPy

# Title of the app
st.title("🎵 Audio Crossfade Mixer")

# Description of the app
st.write("Select two demo tracks, and we'll mix them using a crossfade effect or beatmatch them. Adjust the sliders to customize the audio length.")

# Function to load audio from a public URL
def load_audio_from_url(url):
    audio_data = requests.get(url).content
    return AudioSegment.from_file(BytesIO(audio_data), format="mp3")

# Public demo track URLs from Supabase
demo_tracks = {
    "Boom Bap Flick - Quincas Moreira": "https://eexoqhyrxkhxjvgdbycw.supabase.co/storage/v1/object/public/demo_tracks/Boom_Bap_Flick_Quincas_Moreira_compressed.mp3",
    "ILY Baby - Dyalla": "https://eexoqhyrxkhxjvgdbycw.supabase.co/storage/v1/object/public/demo_tracks/ILY_Baby_Dyalla_compressed.mp3",
    "Fred Again": "https://eexoqhyrxkhxjvgdbycw.supabase.co/storage/v1/object/public/demo_tracks/FredAgain.mp3?t=2024-10-17T22%3A03%3A38.358Z",
    "Da Fonk (feat. Joni)": "https://eexoqhyrxkhxjvgdbycw.supabase.co/storage/v1/object/public/demo_tracks/Da%20Fonk%20(feat.%20Joni).mp3?t=2024-10-17T22%3A03%3A55.830Z",
    "Harlem Shake - Build up": "https://eexoqhyrxkhxjvgdbycw.supabase.co/storage/v1/object/public/demo_tracks/Harlem%20Shake%20-%20Build%20up.mp3?t=2024-12-17T18%3A04%3A02.371Z",
    "One More Time - Build up": "https://eexoqhyrxkhxjvgdbycw.supabase.co/storage/v1/object/public/demo_tracks/One%20More%20Time%20-%20Build%20up.mp3",
}

# Function to load audio from a demo track
def load_audio(selection):
    return load_audio_from_url(demo_tracks[selection])

# Function to crossfade two audio files with adjustable start time and transition length
def crossfade_audio(file1, file2, start_time, fade_duration):
    # Convert to milliseconds
    start_time_ms = start_time * 1000
    fade_duration_ms = fade_duration * 1000

    # Use only the first 20 seconds (20000 ms) of each track
    audio1 = file1[:20000]
    audio2 = file2[:20000]

    # The crossfade will happen starting at start_time_ms of audio1
    # The overlapping region is fade_duration_ms long.

    # Segment of audio1 up to the point we start crossfading plus the fade duration
    # This ensures we have a portion to fade out.
    part1 = audio1[:start_time_ms + fade_duration_ms]

    # Segment of audio2 starting from start_time_ms
    # We want to fade this in at the overlap.
    part2 = audio2[start_time_ms:]

    # Apply fade out to the last fade_duration_ms of part1
    # This means the last fade_duration_ms chunk of part1 will gradually decrease in volume.
    part1_faded = part1.fade_out(fade_duration_ms)

    # Apply fade in to the first fade_duration_ms of part2
    # This will make part2 start quietly and become louder over the fade period.
    part2_faded = part2.fade_in(fade_duration_ms)

    # Now overlay part2_faded onto part1_faded starting at start_time_ms.
    # This creates a smooth crossfade as one fades out and the other fades in.
    final_audio = part1_faded.overlay(part2_faded, position=start_time_ms)

    # Ensure the final audio is 20 seconds long
    final_audio = final_audio[:20000]

    output = BytesIO()
    final_audio.export(output, format="mp3")
    output.seek(0)
    return output.getvalue()

# Function to overlay two audio files based on their BPM
def beatmatch_audio(audio1, audio2):
    # Use only the first 20 seconds of each track
    audio1 = audio1[:20000]
    audio2 = audio2[:20000]

    # Calculate the BPM of each track
    bpm1 = calculate_bpm(audio1)
    bpm2 = calculate_bpm(audio2)

    # Adjust the tempo of the second track to match the first
    if bpm1 and bpm2:
        # Calculate the rate to adjust the second audio's frame rate
        rate = bpm1 / bpm2
        audio2 = audio2._spawn(audio2.raw_data, overrides={"frame_rate": int(audio2.frame_rate * rate)})

    # Overlay the two audio tracks
    final_audio = audio1.overlay(audio2)

    # Ensure the final audio is 20 seconds long
    final_audio = final_audio[:20000]

    output = BytesIO()
    final_audio.export(output, format="mp3")
    output.seek(0)
    return output.getvalue()  # Return the binary data

# Function to calculate the BPM of an audio file
def calculate_bpm(audio):
    audio_wav = BytesIO()
    audio.export(audio_wav, format="wav")
    audio_wav.seek(0)

    y, sr = librosa.load(audio_wav, sr=None)
    try:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        return float(tempo[0]) if isinstance(tempo, (list, np.ndarray)) else float(tempo)
    except Exception as e:
        st.error(f"Error calculating BPM: {e}")
        return None

# Select the first track
st.write("### First Audio Track")
selection1 = st.selectbox("Choose the first audio track", list(demo_tracks.keys()))

# Load the selected audio for the first track
audio1 = load_audio(selection1)

# Preview the original song for the first track
st.audio(demo_tracks[selection1], format="audio/mp3", start_time=0)

# Select the second track
st.write("### Second Audio Track")
selection2 = st.selectbox("Choose the second audio track", list(demo_tracks.keys()))

# Load the selected audio for the second track
audio2 = load_audio(selection2)

# Preview the original song for the second track
st.audio(demo_tracks[selection2], format="audio/mp3", start_time=0)

# Select the mixing option
mix_option = st.selectbox("Choose the mixing option", ["Crossfade", "Beatmatch"])

# Show sliders for crossfade settings only if Crossfade is selected
if mix_option == "Crossfade":
    start_time = st.slider("Start Time for Crossfade (seconds)", min_value=0, max_value=20, value=15, step=1)
    fade_duration = st.slider("Crossfade Duration (seconds)", min_value=1, max_value=20, value=5, step=1)

# Process and mix the audio files if both tracks are selected
if audio1 and audio2:
    # Display BPMs regardless of the mixing option
    bpm1 = calculate_bpm(audio1)
    bpm2 = calculate_bpm(audio2)

    if bpm1 is not None:
        st.write(f"BPM of {selection1}: **{bpm1:.2f}**")
    else:
        st.write(f"BPM of {selection1}: **Unknown**")
    if bpm2 is not None:
        st.write(f"BPM of {selection2}: **{bpm2:.2f}**")
    else:
        st.write(f"BPM of {selection2}: **Unknown**")

    if mix_option == "Crossfade":
        output_audio = crossfade_audio(audio1, audio2, start_time, fade_duration)
    elif mix_option == "Beatmatch":
        output_audio = beatmatch_audio(audio1, audio2)
    
    st.audio(output_audio, format="audio/mp3")  # Now this should work correctly