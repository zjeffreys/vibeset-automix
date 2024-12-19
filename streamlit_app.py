import streamlit as st
from pydub import AudioSegment
from io import BytesIO
import requests
import librosa
import soundfile as sf
import numpy as np

# Title of the app
st.title("🎵 Audio Mixer")

# Description of the app
st.write(
    "Select two demo tracks, and we'll mix them using Automix, Crossfade, or Beatmatch.\n"
    "- Automix: We beatmatch, then crossfade at your chosen time, then continue playing the ENTIRE second track after the crossfade.\n"
    "- If the final mix exceeds 60 seconds, we'll fade out at the 60-second mark.\n"
    "If it's shorter than 60 seconds total, you'll get the entire final mix."
)

def load_audio_from_url(url):
    audio_data = requests.get(url).content
    return AudioSegment.from_file(BytesIO(audio_data), format="mp3")

demo_tracks = {
    "Harlem Shake - Build up": "https://eexoqhyrxkhxjvgdbycw.supabase.co/storage/v1/object/public/demo_tracks/Harlem%20Shake%20-%20Build%20up.mp3?t=2024-12-17T18%3A04%3A02.371Z",
    "One More Time - Build up": "https://eexoqhyrxkhxjvgdbycw.supabase.co/storage/v1/object/public/demo_tracks/One%20More%20Time%20-%20Build%20up.mp3",
    "This Is What It Feels Like - Armin Van Buren": "https://eexoqhyrxkhxjvgdbycw.supabase.co/storage/v1/object/public/demo_tracks/This%20Is%20What%20It%20Feels%20Like%20-%20Armin%20Van%20Buren.mp3?t=2024-12-18T18%3A08%3A03.970Z",
    "Avicii - Faster Than Light ft. Sandro Cavazza (High Quality)": "https://eexoqhyrxkhxjvgdbycw.supabase.co/storage/v1/object/public/demo_tracks/Avicii%20-%20Faster%20Than%20Light%20ft.%20Sandro%20Cavazza%20(High%20Quality).mp3?t=2024-12-18T18%3A14%3A14.717Z",
    "Boom Bap Flick - Quincas Moreira": "https://eexoqhyrxkhxjvgdbycw.supabase.co/storage/v1/object/public/demo_tracks/Boom_Bap_Flick_Quincas_Moreira_compressed.mp3",
    "ILY Baby - Dyalla": "https://eexoqhyrxkhxjvgdbycw.supabase.co/storage/v1/object/public/demo_tracks/ILY_Baby_Dyalla_compressed.mp3",
    "Fred Again": "https://eexoqhyrxkhxjvgdbycw.supabase.co/storage/v1/object/public/demo_tracks/FredAgain.mp3?t=2024-10-17T22%3A03%3A38.358Z",
    "Da Fonk (feat. Joni)": "https://eexoqhyrxkhxjvgdbycw.supabase.co/storage/v1/object/public/demo_tracks/Da%20Fonk%20(feat.%20Joni).mp3?t=2024-10-17T22%3A03%3A55.830Z",
}

def load_audio(selection):
    return load_audio_from_url(demo_tracks[selection])

def export_audio(audio):
    output = BytesIO()
    audio.export(output, format="mp3")
    output.seek(0)
    return output.getvalue()

def calculate_bpm(audio):
    audio_wav = BytesIO()
    audio.export(audio_wav, format="wav")
    audio_wav.seek(0)
    y, sr = librosa.load(audio_wav, sr=None)
    try:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        if isinstance(tempo, (list, np.ndarray)):
            return float(tempo[0])
        else:
            return float(tempo)
    except Exception:
        return None

def crossfade_audio(file1, file2, start_time, fade_duration):
    start_time_ms = start_time * 1000
    fade_duration_ms = fade_duration * 1000

    part1 = file1[:start_time_ms + fade_duration_ms]
    part2 = file2[start_time_ms:]  # Continue second track from start_time_ms

    part1_faded = part1.fade_out(fade_duration_ms)
    part2_faded = part2.fade_in(fade_duration_ms)

    final_audio = part1_faded.overlay(part2_faded, position=start_time_ms)

    # Limit crossfade result to 60s max if needed
    max_length_ms = 60000
    if len(final_audio) > max_length_ms:
        final_audio = final_audio[:max_length_ms].fade_out(2000)

    return final_audio

def beatmatch_audio(audio1, audio2):
    bpm1 = calculate_bpm(audio1)
    bpm2 = calculate_bpm(audio2)

    if bpm1 and bpm2 and bpm2 > 0:
        rate = bpm1 / bpm2
        audio2 = audio2._spawn(audio2.raw_data, overrides={"frame_rate": int(audio2.frame_rate * rate)}).set_frame_rate(audio1.frame_rate)

    final_audio = audio1.overlay(audio2)

    # Limit beatmatch result to 60s max if needed
    max_length_ms = 60000
    if len(final_audio) > max_length_ms:
        final_audio = final_audio[:max_length_ms].fade_out(2000)

    return final_audio

def automix_audio(audio1, audio2, start_time, fade_duration_sec=5):
    # Beatmatch first
    bpm1 = calculate_bpm(audio1)
    bpm2 = calculate_bpm(audio2)
    print(f"BPM of audio1: {bpm1}, BPM of audio2: {bpm2}")  # Debug BPM values

    if bpm1 and bpm2 and bpm2 > 0:
        rate = bpm1 / bpm2
        print(f"Rate adjustment for audio2: {rate}")  # Debug rate adjustment
        audio2 = audio2._spawn(audio2.raw_data, overrides={"frame_rate": int(audio2.frame_rate * rate)}).set_frame_rate(audio1.frame_rate)

    # Crossfade
    fade_duration = fade_duration_sec  # Fixed fade duration
    start_time_ms = start_time * 1000
    fade_duration_ms = fade_duration * 1000

    # part1: up to start_time + fade
    part1 = audio1[:start_time_ms + fade_duration_ms]
    print(f"Length of part1: {len(part1) / 1000:.2f} seconds")  # Debug length of part1

    # part2: entire second track (no slicing)
    part2 = audio2  
    print(f"Length of part2 (full audio2): {len(part2) / 1000:.2f} seconds")  # Debug length of part2

    part1_faded = part1.fade_out(fade_duration_ms)
    part2_faded = part2.fade_in(fade_duration_ms)

    # Overlay second track starting at start_time in the final mix
    final_audio = part1_faded.overlay(part2_faded, position=start_time_ms)
    print(f"Length of final_audio after overlay: {len(final_audio) / 1000:.2f} seconds")  # Debug length of final_audio

    # Now final_audio includes the entire second track starting at start_time.
    # If the total length > 60s, we fade out at 60s, else keep full length.
    max_length_ms = 60000
    if len(final_audio) > max_length_ms:
        final_audio = final_audio[:max_length_ms].fade_out(2000)
        print(f"Length of final_audio after truncation and fade out: {len(final_audio) / 1000:.2f} seconds")  # Debug truncated length

    return final_audio



selection1 = st.selectbox("Choose the first audio track", list(demo_tracks.keys()))
audio1 = load_audio(selection1)
st.audio(demo_tracks[selection1], format="audio/mp3", start_time=0)
st.write(f"Length of {selection1} (sec): {len(audio1)/1000:.2f}")

st.write("### Second Audio Track")
selection2 = st.selectbox("Choose the second audio track", list(demo_tracks.keys()))
audio2 = load_audio(selection2)
st.audio(demo_tracks[selection2], format="audio/mp3", start_time=0)
st.write(f"Length of {selection2} (sec): {len(audio2)/1000:.2f}")

mix_option = st.selectbox("Choose the mixing option", ["Automix", "Crossfade", "Beatmatch"])

if mix_option == "Crossfade":
    start_time = st.slider("Start Time for Crossfade (seconds)", min_value=0, max_value=60, value=15, step=1)
    fade_duration = st.slider("Crossfade Duration (seconds)", min_value=1, max_value=20, value=5, step=1)
elif mix_option == "Automix":
    start_time = st.slider("When should the first track begin fading? (seconds)", min_value=5, max_value=60, value=10, step=1)
    fade_duration_sec = st.slider("Fade Duration", min_value=5, max_value=20, value=10, step=1)

# Process
if audio1 and audio2:
    bpm1 = calculate_bpm(audio1)
    bpm2 = calculate_bpm(audio2)

    bpm_info_1 = f"BPM of {selection1}: **{bpm1:.2f}**" if bpm1 else f"BPM of {selection1}: **Unknown**"
    bpm_info_2 = f"BPM of {selection2}: **{bpm2:.2f}**" if bpm2 else f"BPM of {selection2}: **Unknown**"

    if mix_option == "Crossfade":
        final_audio = crossfade_audio(audio1, audio2, start_time, fade_duration)
        merge_info = f"The two tracks were crossfaded starting at {start_time}s with a fade duration of {fade_duration}s."
    elif mix_option == "Beatmatch":
        final_audio = beatmatch_audio(audio1, audio2)
        merge_info = "The two tracks were beatmatched by adjusting the tempo of the second track to match the first."
    elif mix_option == "Automix":
        final_audio = automix_audio(audio1, audio2, start_time, fade_duration_sec)
        merge_info = (
            f"The two tracks were beatmatched and then crossfaded starting at {start_time}s. "
            "After the crossfade, the ENTIRE second track continues to play. If the final mix exceeds 60s, "
            "it is faded out at the 60s mark."
        )

    # Calculate final BPM
    final_bpm = calculate_bpm(final_audio)
    final_bpm_info = f"BPM of Final Output: **{final_bpm:.2f}**" if final_bpm else "BPM of Final Output: **Unknown**"

    output_audio = export_audio(final_audio)

    # Display info
    st.header("This is the final song!")
    st.write(bpm_info_1)
    st.write(bpm_info_2)
    st.write(final_bpm_info)
    st.write(f"Final Length: {len(final_audio)/1000:.2f} sec")
    st.write(merge_info)

    st.audio(output_audio, format="audio/mp3")