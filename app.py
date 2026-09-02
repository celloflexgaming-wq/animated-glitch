import streamlit as st
import numpy as np
from PIL import Image
import subprocess
import tempfile
import os
import shutil
import math

# ---------------------------------------------------------
# PAGE
# ---------------------------------------------------------

st.set_page_config(
    page_title="Animated Pixel Glitch",
    page_icon="🎞️",
    layout="centered"
)

st.title("🎞️ Animated Pixel Glitch")
st.write(
    "Upload een foto en maak er een vloeiende pixel-stretch/glitch-video van."
)

# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

uploaded_file = st.file_uploader(
    "📷 Kies een foto",
    type=["jpg", "jpeg", "png", "webp"]
)

col1, col2 = st.columns(2)

with col1:
    duration = st.selectbox(
        "⏱️ Duur",
        [5, 10, 15],
        index=2
    )

with col2:
    fps = st.selectbox(
        "🎞️ FPS",
        [24, 30, 60],
        index=1
    )

resolution = st.selectbox(
    "🖼️ Maximale breedte",
    [800, 1280, 1920],
    index=2
)

intensity = st.slider(
    "⚡ Glitch intensiteit",
    min_value=1,
    max_value=10,
    value=6
)

speed = st.slider(
    "🌊 Bewegingssnelheid",
    min_value=1,
    max_value=5,
    value=3
)

if uploaded_file is None:
    st.info("👆 Upload hierboven een foto om te beginnen.")
    st.stop()


# ---------------------------------------------------------
# LOAD IMAGE
# ---------------------------------------------------------

try:
    image = Image.open(uploaded_file).convert("RGB")
except Exception as e:
    st.error("De afbeelding kon niet worden geopend.")
    st.exception(e)
    st.stop()


# ---------------------------------------------------------
# RESIZE
# ---------------------------------------------------------

original_width, original_height = image.size

if original_width > resolution:
    scale = resolution / original_width
    new_width = resolution
    new_height = int(original_height * scale)

    image = image.resize(
        (new_width, new_height),
        Image.Resampling.LANCZOS
    )

else:
    new_width = original_width
    new_height = original_height


img = np.asarray(image, dtype=np.uint8)

height, width, _ = img.shape


# ---------------------------------------------------------
# INFORMATION
# ---------------------------------------------------------

frames_total = int(duration * fps)

st.write(
    f"**Output:** {width} × {height} · "
    f"{fps} FPS · {duration} seconden · "
    f"{frames_total} frames"
)


# ---------------------------------------------------------
# CREATE GLITCH BANDS
# ---------------------------------------------------------

rng = np.random.default_rng(12345)

bands = []

# Meer intensiteit = meer en kleinere banden
number_of_bands = int(
    20 + intensity * 10
)

# Maak ongeveer gelijk verdeelde horizontale zones
positions = np.linspace(
    0,
    height,
    number_of_bands + 1,
    dtype=int
)

for i in range(number_of_bands):

    y1 = positions[i]
    y2 = positions[i + 1]

    if y2 <= y1:
        continue

    band_height = y2 - y1

    # Willekeurige horizontale segmenten
    segments = int(
        rng.integers(
            2,
            4 + intensity // 2
        )
    )

    split_points = sorted(
        rng.choice(
            np.arange(1, width),
            size=min(segments - 1, max(1, width - 1)),
            replace=False
        ).tolist()
    )

    split_points = [0] + split_points + [width]

    band_segments = []

    for s in range(len(split_points) - 1):

        x1 = split_points[s]
        x2 = split_points[s + 1]

        if x2 <= x1:
            continue

        # Kies een willekeurige verticale bronkolom
        source_x = int(
            rng.integers(
                x1,
                max(x1 + 1, x2)
            )
        )

        # Neem een verticale strook uit de originele afbeelding
        source = img[
            y1:y2,
            source_x:source_x + 1,
            :
        ]

        # Rek deze horizontaal uit
        stretched = np.repeat(
            source,
            x2 - x1,
            axis=1
        )

        band_segments.append(
            (
                x1,
                x2,
                stretched
            )
        )

    # Iedere band krijgt een eigen snelheid/fase
    cycles = int(
        rng.integers(
            1,
            speed + 1
        )
    )

    direction = int(
        rng.choice([-1, 1])
    )

    # Extra kleine faseverschillen
    phase = float(
        rng.random()
    )

    bands.append(
        {
            "y1": y1,
            "y2": y2,
            "segments": band_segments,
            "cycles": cycles,
            "direction": direction,
            "phase": phase,
            "height": band_height
        }
    )


# ---------------------------------------------------------
# TEMPORARY DIRECTORY
# ---------------------------------------------------------

temp_dir = tempfile.mkdtemp(
    prefix="glitch_frames_"
)

output_file = os.path.join(
    temp_dir,
    "animated_glitch.mp4"
)


# ---------------------------------------------------------
# GENERATE VIDEO
# ---------------------------------------------------------

if st.button(
    "🎬 Genereer 15 seconden MP4",
    type="primary",
    use_container_width=True
):

    progress = st.progress(
        0,
        text="Animatie voorbereiden..."
    )

    status = st.empty()

    try:

        # -------------------------------------------------
        # FFmpeg input
        # -------------------------------------------------

        ffmpeg_command = [
            "ffmpeg",

            "-y",

            "-f", "rawvideo",
            "-vcodec", "rawvideo",

            "-pix_fmt", "rgb24",

            "-s",
            f"{width}x{height}",

            "-r",
            str(fps),

            "-i",
            "-",

            "-an",

            "-c:v",
            "libx264",

            "-preset",
            "medium",

            "-crf",
            "18",

            "-pix_fmt",
            "yuv420p",

            "-movflags",
            "+faststart",

            output_file
        ]

        process = subprocess.Popen(
            ffmpeg_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # -------------------------------------------------
        # GENERATE FRAMES
        # -------------------------------------------------

        for frame_index in range(frames_total):

            # 0 -> 1
            t = frame_index / frames_total

            frame = img.copy()

            for band in bands:

                y1 = band["y1"]
                y2 = band["y2"]

                # Exact periodieke beweging
                phase_position = (
                    t * band["cycles"]
                    + band["phase"]
                )

                offset = int(
                    round(
                        phase_position
                        * width
                    )
                )

                offset *= band["direction"]

                for x1, x2, stretched in band["segments"]:

                    segment_width = x2 - x1

                    shifted = np.roll(
                        stretched,
                        offset % max(1, segment_width),
                        axis=1
                    )

                    frame[
                        y1:y2,
                        x1:x2,
                        :
                    ] = shifted

            # -------------------------------------------------
            # Write frame directly into FFmpeg
            # -------------------------------------------------

            process.stdin.write(
                frame.astype(
                    np.uint8,
                    copy=False
                ).tobytes()
            )

            percent = (
                frame_index + 1
            ) / frames_total

            progress.progress(
                percent,
                text=(
                    f"Frames renderen: "
                    f"{frame_index + 1}/{frames_total}"
                )
            )

            status.write(
                f"🎞️ Frame {frame_index + 1} van {frames_total}"
            )

        process.stdin.close()

        # Wait for FFmpeg
        stdout, stderr = process.communicate()

        if process.returncode != 0:

            st.error(
                "❌ FFmpeg kon de video niet maken."
            )

            st.code(
                stderr.decode(
                    "utf-8",
                    errors="replace"
                )
            )

            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

            st.stop()


        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        progress.progress(
            1.0,
            text="✅ Video klaar!"
        )

        status.empty()

        if os.path.exists(output_file):

            file_size = os.path.getsize(
                output_file
            )

            st.success(
                f"🎉 Klaar! "
                f"MP4-grootte: "
                f"{file_size / 1024 / 1024:.1f} MB"
            )

            # Video preview
            with open(
                output_file,
                "rb"
            ) as video_file:

                video_data = video_file.read()

            st.video(
                video_data
            )

            # Download
            st.download_button(
                label="⬇️ Download MP4",
                data=video_data,
                file_name="animated_pixel_glitch.mp4",
                mime="video/mp4",
                use_container_width=True
            )

        else:

            st.error(
                "❌ Het MP4-bestand is niet gevonden."
            )

    except Exception as e:

        st.error(
            "❌ Er ging iets mis tijdens het renderen."
        )

        st.exception(e)

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )
