import streamlit as st
import numpy as np
from PIL import Image
import subprocess
import tempfile
import os
import math

st.set_page_config(page_title="Smooth Glitch Video", layout="centered")

st.title("🎞️ Smooth Glitch Video")

uploaded = st.file_uploader(
    "Upload een foto",
    type=["jpg", "jpeg", "png", "webp"]
)

if uploaded:

    img = Image.open(uploaded).convert("RGB")

    st.image(img, caption="Originele foto", use_container_width=True)

    st.subheader("Instellingen")

    duration = st.selectbox(
        "Duur",
        [5, 10, 15],
        index=2
    )

    fps = st.selectbox(
        "FPS",
        [24, 30, 60],
        index=1
    )

    max_width = st.selectbox(
        "Maximale breedte",
        [800, 1280, 1920],
        index=1
    )

    bands_count = st.slider(
        "Aantal horizontale glitch-banden",
        20,
        150,
        60
    )

    speed = st.slider(
        "Animatiesnelheid",
        1,
        8,
        3
    )

    if st.button("🎬 Maak video", type="primary"):

        # -----------------------------
        # FOTO VOORBEREIDEN
        # -----------------------------

        if img.width > max_width:
            new_height = int(img.height * max_width / img.width)
            img = img.resize(
                (max_width, new_height),
                Image.Resampling.LANCZOS
            )

        img_array = np.array(img, dtype=np.uint8)

        height, width, channels = img_array.shape

        # -----------------------------
        # RANDOM GENERATOR
        # -----------------------------

        rng = np.random.default_rng(42)

        # -----------------------------
        # BANDS MAKEN
        # -----------------------------

        band_edges = np.linspace(
            0,
            height,
            bands_count + 1
        ).astype(int)

        bands = []

        for i in range(bands_count):

            y_start = band_edges[i]
            y_end = band_edges[i + 1]

            band_height = y_end - y_start

            if band_height <= 0:
                continue

            # Volledige breedte van de band
            band_row = np.zeros(
                (band_height, width, 3),
                dtype=np.uint8
            )

            # 1 t/m 5 verticale segmenten
            num_segments = int(
                rng.integers(1, 6)
            )

            if num_segments == 1:

                splits = [0, width]

            else:

                split_points = sorted(
                    rng.choice(
                        np.arange(1, width),
                        size=num_segments - 1,
                        replace=False
                    ).tolist()
                )

                splits = [0] + split_points + [width]

            # -----------------------------
            # IEDER SEGMENT VULLEN
            # -----------------------------

            for j in range(len(splits) - 1):

                x_start = splits[j]
                x_end = splits[j + 1]

                if x_end <= x_start:
                    continue

                # Willekeurige verticale positie
                sample_x = int(
                    rng.integers(
                        x_start,
                        x_end
                    )
                )

                # Neem één verticale strook uit de originele foto
                source = img_array[
                    y_start:y_end,
                    sample_x:sample_x + 1,
                    :
                ]

                # Rek deze strook horizontaal uit
                band_row[
                    :,
                    x_start:x_end,
                    :
                ] = np.repeat(
                    source,
                    x_end - x_start,
                    axis=1
                )

            # -----------------------------
            # ANIMATIE-INSTELLINGEN
            # -----------------------------

            direction = int(
                rng.choice([-1, 1])
            )

            # Verschillende bewegingssnelheden
            cycles = int(
                rng.integers(
                    1,
                    speed + 1
                )
            )

            # Willekeurige startpositie
            phase = float(
                rng.random()
            )

            bands.append({
                "y_start": y_start,
                "y_end": y_end,
                "row": band_row,
                "direction": direction,
                "cycles": cycles,
                "phase": phase
            })

        # -----------------------------
        # VIDEO INSTELLINGEN
        # -----------------------------

        total_frames = int(
            duration * fps
        )

        st.write(
            f"Video: {width} × {height} px — "
            f"{total_frames} frames"
        )

        progress = st.progress(0)

        # -----------------------------
        # TIJDELIJKE OUTPUT
        # -----------------------------

        output_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".mp4"
        )

        output_path = output_file.name
        output_file.close()

        # -----------------------------
        # FFMPEG STARTEN
        # -----------------------------

        command = [
            "ffmpeg",

            "-y",

            "-loglevel",
            "error",

            "-f",
            "rawvideo",

            "-vcodec",
            "rawvideo",

            "-pix_fmt",
            "rgb24",

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

            output_path
        ]

        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # -----------------------------
        # FRAMES MAKEN
        # -----------------------------

        try:

            for frame_number in range(total_frames):

                # Tijd van huidige frame
                t = frame_number / fps

                frame = np.zeros_like(
                    img_array
                )

                # -----------------------------
                # ALLE BANDS ANIMEREN
                # -----------------------------

                for band in bands:

                    y1 = band["y_start"]
                    y2 = band["y_end"]

                    band_row = band["row"]

                    direction = band["direction"]
                    cycles = band["cycles"]
                    phase = band["phase"]

                    # --------------------------------
                    # VLOEIENDE HORIZONTALE BEWEGING
                    # --------------------------------
                    #
                    # De sinus zorgt ervoor dat de band
                    # soepel heen en weer beweegt.
                    #
                    movement = (
                        0.5
                        + 0.5
                        * math.sin(
                            2
                            * math.pi
                            * (
                                cycles
                                * t
                                / duration
                                + phase
                            )
                        )
                    )

                    # Van -breedte/2 tot +breedte/2
                    shift = int(
                        (
                            movement - 0.5
                        )
                        * width
                        * direction
                    )

                    # Band over de VOLLEDIGE breedte
                    shifted = np.roll(
                        band_row,
                        shift,
                        axis=1
                    )

                    frame[
                        y1:y2,
                        :,
                        :
                    ] = shifted

                # -----------------------------
                # FRAME NAAR FFMPEG
                # -----------------------------

                process.stdin.write(
                    frame.tobytes()
                )

                # Progress
                if frame_number % max(1, fps // 2) == 0:

                    progress.progress(
                        min(
                            1.0,
                            (frame_number + 1)
                            / total_frames
                        )
                    )

            process.stdin.close()

            stderr = process.stderr.read()

            return_code = process.wait()

            if return_code != 0:

                st.error(
                    "FFmpeg kon de video niet maken:\n\n"
                    + stderr.decode(
                        "utf-8",
                        errors="replace"
                    )
                )

                raise RuntimeError(
                    "FFmpeg error"
                )

        except Exception:

            try:
                process.stdin.close()
            except:
                pass

            process.kill()

            raise

        progress.progress(1.0)

        # -----------------------------
        # VIDEO TONEN
        # -----------------------------

        with open(
            output_path,
            "rb"
        ) as f:

            video_bytes = f.read()

        st.success(
            "✅ Video klaar!"
        )

        st.video(
            video_bytes
        )

        st.download_button(
            label="⬇️ Download MP4",
            data=video_bytes,
            file_name="smooth_glitch.mp4",
            mime="video/mp4"
        )

        # Tijdelijk bestand verwijderen
        try:
            os.remove(output_path)
        except:
            pass
