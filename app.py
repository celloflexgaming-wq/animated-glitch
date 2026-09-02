import streamlit as st
import numpy as np
from PIL import Image
import subprocess
import tempfile
import os
import shutil


# =========================================================
# PAGINA
# =========================================================

st.set_page_config(
    page_title="Animated Glitch",
    page_icon="🎞️",
    layout="centered"
)

st.title("🎞️ Animated Glitch")
st.write(
    "De volledige foto wordt omgezet in vloeiende bewegende "
    "pixel-stretch banden."
)


# =========================================================
# FOTO UPLOAD
# =========================================================

uploaded_file = st.file_uploader(
    "📷 Upload een foto",
    type=["jpg", "jpeg", "png", "webp"]
)

if uploaded_file is None:
    st.info("Upload hierboven een foto om te beginnen.")
    st.stop()


# =========================================================
# INSTELLINGEN
# =========================================================

st.subheader("⚙️ Video instellingen")

col1, col2 = st.columns(2)

with col1:

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


with col2:

    max_width = st.selectbox(
        "Maximale breedte",
        [800, 1280, 1920],
        index=2
    )

    quality = st.selectbox(
        "Kwaliteit",
        ["Hoog", "Zeer hoog", "Maximaal"],
        index=1
    )


st.subheader("⚡ Glitch instellingen")

intensity = st.slider(
    "Aantal glitch-banden",
    min_value=20,
    max_value=150,
    value=70
)

segments = st.slider(
    "Stroken per band",
    min_value=1,
    max_value=6,
    value=3
)

speed = st.slider(
    "Bewegingssnelheid",
    min_value=1,
    max_value=8,
    value=4
)


# =========================================================
# FOTO LADEN
# =========================================================

try:

    image = Image.open(
        uploaded_file
    ).convert("RGB")

except Exception as e:

    st.error("De afbeelding kon niet worden geopend.")
    st.exception(e)
    st.stop()


# =========================================================
# RESIZE
# =========================================================

original_width, original_height = image.size


if original_width > max_width:

    scale = max_width / original_width

    width = max_width

    height = int(
        original_height * scale
    )

    image = image.resize(
        (width, height),
        Image.Resampling.LANCZOS
    )

else:

    width = original_width
    height = original_height


img = np.asarray(
    image,
    dtype=np.uint8
)


# =========================================================
# PREVIEW
# =========================================================

st.image(
    image,
    caption=f"Origineel · {width} × {height}",
    use_container_width=True
)


frames_total = int(
    duration * fps
)


st.write(
    f"🎬 {width} × {height} · "
    f"{fps} FPS · "
    f"{duration} seconden · "
    f"{frames_total} frames"
)


# =========================================================
# GLITCH BANDEN MAKEN
#
# BELANGRIJK:
# Het volledige beeld wordt verdeeld over banden.
# Er blijft dus GEEN normaal gedeelte over.
# =========================================================

rng = np.random.default_rng(47291)

bands = []


# Verdeel volledige hoogte
# exact over alle banden.

band_edges = np.linspace(
    0,
    height,
    intensity + 1
).astype(int)


for band_index in range(intensity):

    y1 = int(
        band_edges[band_index]
    )

    y2 = int(
        band_edges[band_index + 1]
    )


    if y2 <= y1:
        continue


    band_height = y2 - y1


    # -----------------------------------------------------
    # Willekeurige horizontale segmenten
    # -----------------------------------------------------

    possible_splits = np.arange(
        1,
        width
    )


    split_count = min(
        segments - 1,
        len(possible_splits)
    )


    if split_count > 0:

        split_points = sorted(
            rng.choice(
                possible_splits,
                size=split_count,
                replace=False
            ).tolist()
        )

    else:

        split_points = []


    split_points = (
        [0]
        + split_points
        + [width]
    )


    band_segments = []


    for segment_index in range(
        len(split_points) - 1
    ):

        x1 = int(
            split_points[segment_index]
        )

        x2 = int(
            split_points[segment_index + 1]
        )


        if x2 <= x1:
            continue


        # -------------------------------------------------
        # Kies willekeurige verticale bronkolom
        # -------------------------------------------------

        source_x = int(
            rng.integers(
                x1,
                max(
                    x1 + 1,
                    x2
                )
            )
        )


        # -------------------------------------------------
        # Neem verticale pixelstrook
        # -------------------------------------------------

        source = img[
            y1:y2,
            source_x:source_x + 1,
            :
        ]


        # -------------------------------------------------
        # Stretch deze pixel horizontaal
        # -------------------------------------------------

        segment_width = x2 - x1


        stretched = np.repeat(
            source,
            segment_width,
            axis=1
        )


        # -------------------------------------------------
        # Bewegingsparameters
        # -------------------------------------------------

        direction = int(
            rng.choice(
                [-1, 1]
            )
        )


        # Iedere band een eigen aantal bewegingen
        cycles = float(
            rng.uniform(
                0.6,
                1.8
            )
            * speed
            / 4.0
        )


        # Willekeurige startpositie
        phase = float(
            rng.random()
        )


        band_segments.append(
            {
                "x1": x1,
                "x2": x2,
                "data": stretched,
                "direction": direction,
                "cycles": cycles,
                "phase": phase
            }
        )


    bands.append(
        {
            "y1": y1,
            "y2": y2,
            "segments": band_segments
        }
    )


# =========================================================
# KWALITEIT
# =========================================================

if quality == "Hoog":

    crf = 21
    preset = "veryfast"

elif quality == "Zeer hoog":

    crf = 18
    preset = "medium"

else:

    crf = 16
    preset = "slow"


# =========================================================
# TEMPORARY DIRECTORY
# =========================================================

temp_dir = tempfile.mkdtemp(
    prefix="animated_glitch_"
)

output_path = os.path.join(
    temp_dir,
    "animated_glitch.mp4"
)


# =========================================================
# GENERATE
# =========================================================

if st.button(
    "🎬 Genereer 15 seconden glitch-video",
    type="primary",
    use_container_width=True
):

    progress = st.progress(
        0,
        text="Video voorbereiden..."
    )

    status = st.empty()


    # =====================================================
    # FFMPEG
    # =====================================================

    ffmpeg_command = [

        "ffmpeg",

        "-y",

        "-f",
        "rawvideo",

        "-pix_fmt",
        "rgb24",

        "-video_size",
        f"{width}x{height}",

        "-framerate",
        str(fps),

        "-i",
        "pipe:0",

        "-an",

        "-c:v",
        "libx264",

        "-preset",
        preset,

        "-crf",
        str(crf),

        "-pix_fmt",
        "yuv420p",

        "-movflags",
        "+faststart",

        output_path
    ]


    process = None


    try:

        process = subprocess.Popen(
            ffmpeg_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )


        # =================================================
        # FRAMES GENEREREN
        # =================================================

        for frame_index in range(
            frames_total
        ):

            # -------------------------------------------------
            # Tijdpositie
            #
            # 0.0 -> begin
            # bijna 1.0 -> einde
            #
            # Door sinusbeweging ontstaat een vloeiende loop.
            # -------------------------------------------------

            t = (
                frame_index
                / frames_total
            )


            # -------------------------------------------------
            # Nieuw frame
            #
            # We vullen het VOLLEDIG met glitch-banden.
            # -------------------------------------------------

            frame = np.zeros_like(
                img
            )


            # =================================================
            # ELKE BAND
            # =================================================

            for band in bands:

                y1 = band["y1"]
                y2 = band["y2"]


                # -------------------------------------------------
                # ELK SEGMENT
                # -------------------------------------------------

                for segment in band["segments"]:

                    x1 = segment["x1"]
                    x2 = segment["x2"]

                    segment_width = (
                        x2 - x1
                    )


                    if segment_width <= 0:
                        continue


                    # -------------------------------------------------
                    # VLOEIENDE SINUSBEWEGING
                    #
                    # Geen harde sprong van rechts terug naar links.
                    # -------------------------------------------------

                    phase = (
                        (
                            t
                            * 2.0
                            * np.pi
                            * segment["cycles"]
                        )
                        +
                        segment["phase"]
                    )


                    movement = (
                        np.sin(
                            phase
                        )
                        + 1.0
                    ) / 2.0


                    # -------------------------------------------------
                    # Richting
                    # -------------------------------------------------

                    if segment["direction"] > 0:

                        shift = int(
                            movement
                            * max(
                                1,
                                segment_width - 1
                            )
                        )

                    else:

                        shift = int(
                            (
                                1.0
                                - movement
                            )
                            * max(
                                1,
                                segment_width - 1
                            )
                        )


                    # -------------------------------------------------
                    # Beweeg de stretched pixels
                    # -------------------------------------------------

                    moving = np.roll(
                        segment["data"],
                        shift,
                        axis=1
                    )


                    # -------------------------------------------------
                    # Hele segment vullen
                    # -------------------------------------------------

                    frame[
                        y1:y2,
                        x1:x2,
                        :
                    ] = moving[
                        :,
                        :segment_width,
                        :
                    ]


            # =================================================
            # VEILIGHEID
            #
            # Mocht een pixelgebied niet gevuld zijn door
            # afrondingen, dan vullen we het met de originele
            # foto. Normaal gesproken gebeurt dit niet.
            # =================================================

            # Dit zorgt er tevens voor dat er nooit zwarte
            # gaten ontstaan.

            missing = np.all(
                frame == 0,
                axis=2
            )


            if np.any(
                missing
            ):

                frame[
                    missing
                ] = img[
                    missing
                ]


            # =================================================
            # NAAR FFMPEG
            # =================================================

            process.stdin.write(
                frame.tobytes()
            )


            # =================================================
            # PROGRESS
            # =================================================

            percent = (
                frame_index + 1
            ) / frames_total


            progress.progress(
                percent,
                text=(
                    f"〰️ Glitch renderen: "
                    f"{frame_index + 1} / "
                    f"{frames_total}"
                )
            )


            status.write(
                f"Frame {frame_index + 1} van "
                f"{frames_total}"
            )


        # =====================================================
        # FFMPEG AFSLUITEN
        # =====================================================

        process.stdin.close()


        stderr = process.stderr.read().decode(
            "utf-8",
            errors="replace"
        )


        return_code = process.wait()


        # =====================================================
        # FOUT
        # =====================================================

        if return_code != 0:

            st.error(
                "❌ FFmpeg kon de video niet maken."
            )

            st.code(
                stderr[-6000:]
            )

            st.stop()


        # =====================================================
        # CONTROLEREN
        # =====================================================

        if not os.path.exists(
            output_path
        ):

            st.error(
                "❌ MP4-bestand ontbreekt."
            )

            st.stop()


        # =====================================================
        # SUCCES
        # =====================================================

        progress.progress(
            1.0,
            text="✅ Video klaar!"
        )

        status.empty()


        file_size = os.path.getsize(
            output_path
        )


        st.success(
            "🎉 Je volledige glitch-video is klaar!"
        )


        st.write(
            f"Bestandsgrootte: "
            f"**{file_size / 1024 / 1024:.1f} MB**"
        )


        # =====================================================
        # VIDEO
        # =====================================================

        with open(
            output_path,
            "rb"
        ) as f:

            video_data = f.read()


        st.video(
            video_data
        )


        # =====================================================
        # DOWNLOAD
        # =====================================================

        st.download_button(
            label="⬇️ Download MP4",
            data=video_data,
            file_name="animated_glitch.mp4",
            mime="video/mp4",
            use_container_width=True
        )


    except BrokenPipeError:

        st.error(
            "❌ FFmpeg stopte onverwacht."
        )


        if process is not None:

            try:

                error_text = (
                    process.stderr.read()
                    .decode(
                        "utf-8",
                        errors="replace"
                    )
                )

                st.code(
                    error_text[-6000:]
                )

            except Exception:
                pass


    except Exception as e:

        st.error(
            "❌ Er ging iets mis tijdens het renderen."
        )

        st.exception(e)


    finally:

        if process is not None:

            try:

                if process.poll() is None:
                    process.kill()

            except Exception:
                pass


        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )
