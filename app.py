import streamlit as st
import subprocess
import numpy as np
import os
import tempfile

st.set_page_config(page_title="FFmpeg Raw Video Test")

st.title("🎬 FFmpeg Video Test")

width = 640
height = 360
fps = 30
frames = 90

if st.button("Start test", type="primary"):

    output = os.path.join(
        tempfile.gettempdir(),
        "ffmpeg_test.mp4"
    )

    command = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-video_size", f"{width}x{height}",
        "-framerate", str(fps),
        "-i", "pipe:0",
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        output
    ]

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        for i in range(frames):

            # simpele bewegende testafbeelding
            frame = np.zeros(
                (height, width, 3),
                dtype=np.uint8
            )

            x = int(
                (width - 100)
                * i
                / max(1, frames - 1)
            )

            frame[
                100:200,
                x:x + 100,
                0
            ] = 255

            process.stdin.write(
                frame.tobytes()
            )

        process.stdin.close()

        stderr = process.stderr.read().decode(
            "utf-8",
            errors="replace"
        )

        returncode = process.wait()

        if returncode == 0 and os.path.exists(output):

            st.success("✅ FFmpeg video-test werkt!")

            with open(output, "rb") as f:
                data = f.read()

            st.video(data)

            st.download_button(
                "⬇️ Download testvideo",
                data=data,
                file_name="ffmpeg_test.mp4",
                mime="video/mp4"
            )

        else:

            st.error(
                f"❌ FFmpeg stopte met code {returncode}"
            )

            st.code(stderr)

    except Exception as e:

        st.error("❌ Python kreeg een fout")

        st.exception(e)

        try:
            process.kill()
        except Exception:
            pass
