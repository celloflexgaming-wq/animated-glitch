import streamlit as st
import subprocess

st.title("🎬 FFmpeg test")

try:
    result = subprocess.run(
        ["ffmpeg", "-version"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        st.success("✅ FFmpeg is beschikbaar!")
        st.code(result.stdout.splitlines()[0])
    else:
        st.error("❌ FFmpeg is geïnstalleerd maar geeft een fout.")
        st.code(result.stderr)

except Exception as e:
    st.error("❌ FFmpeg is niet gevonden.")
    st.exception(e)
