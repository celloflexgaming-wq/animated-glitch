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
    page_title="Smooth Pixel Stretch",
    page_icon="〰️",
    layout="centered"
)

st.title("〰️ Smooth Pixel Stretch")
st.write(
    "Vloeiende horizontale pixel-stretches die over het beeld bewegen."
)


# =========================================================
# FOTO
# =========================================================

uploaded_file = st.file_uploader(
    "📷 Upload een foto",
    type=["jpg", "jpeg", "png", "webp"]
)

if uploaded_file is None:
    st.info("Upload een foto om te beginnen.")
    st.stop()


# =========================================================
# INSTELLINGEN
# =========================================================

st.subheader("⚙️ Instellingen")

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


st.subheader("〰️ Stretch-effect")

band_amount = st.slider(
    "Aantal bewegende strepen",
    5,
    40,
    18
)

stretch_amount = st.slider(
    "Stretch lengte",
    1.0,
    8.0,
    3.5,
    0.1
)

movement_speed = st.slider(
    "Bewegingssnelheid",
    0.2,
    2.0,
    0.8,
    0.1
)

band_thickness = st.slider(
    "Dikte van de strepen",
    1,
    10,
    4
)


# =========================================================
# AFBEELDING LADEN
# =========================================================

try:

    image = Image.open(
        uploaded_file
    ).convert("RGB")

except Exception as e:

    st.error("De afbeelding kon niet worden geopend.")
    st.exception(e)
    st.stop()


original_width, original_height = image.size


# =========================================================
# RESIZE
# =========================================================

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
# RANDOM GENERATOR
# =========================================================

rng = np.random.default_rng(49281)


# =========================================================
# STRETCH BANDS VOORBEREIDEN
# =========================================================

bands = []


for i in range(band_amount):

    # Willekeurige verticale positie
    y_center = rng.uniform(
        0,
        height
    )

    # Dikte met kleine variatie
    thickness = int(
        max(
            1,
            rng.uniform(
                0.5,
                1.5
            )
            * band_thickness
            * max(
                1,
                height / 500
            )
        )
    )


    y1 = int(
        max(
            0,
            y_center - thickness / 2
        )
    )

    y2 = int(
        min(
            height,
            y1 + thickness
        )
    )


    if y2 <= y1:
        continue


    # -----------------------------------------------------
    # Bronpositie
    # -----------------------------------------------------

    source_y = int(
        np.clip(
            y_center,
            0,
            height - 1
        )
    )


    # Eén horizontale lijn uit de foto
    source_line = img[
        source_y:source_y + 1,
        :,
        :
    ]


    # Maak een horizontale strook
    source_line = np.repeat(
        source_line,
        y2 - y1,
        axis=0
    )


    # -----------------------------------------------------
    # Stretch grootte
    # -----------------------------------------------------

    stretch_factor = rng.uniform(
        1.5,
        stretch_amount
    )


    stretch_width = int(
        width * stretch_factor
    )


    # Herhaal de foto horizontaal
    repeats = int(
        np.ceil(
            stretch_width / width
        )
    )


    stretched = np.tile(
        source_line,
        (1, repeats, 1)
    )


    stretched = stretched[
        :,
        :stretch_width,
        :
    ]


    # -----------------------------------------------------
    # Bewegingsparameters
    # -----------------------------------------------------

    direction = int(
        rng.choice(
            [-1, 1]
        )
    )


    # Verschillende snelheden
    speed = rng.uniform(
        0.55,
        1.35
    )


    # Verschillende startfase
    phase = rng.uniform(
        0,
        2 * np.pi
    )


    # Verticale fade
    alpha = rng.uniform(
        0.65,
        1.0
    )


    bands.append(
        {
            "y1": y1,
            "y2": y2,
            "data": stretched,
            "stretch_width": stretch_width,
            "direction": direction,
            "speed": speed,
            "phase": phase,
            "alpha": alpha
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
# TEMP DIRECTORY
# =========================================================

temp_dir = tempfile.mkdtemp(
    prefix="smooth_glitch_"
)

output_path = os.path.join(
    temp_dir,
    "smooth_pixel_stretch.mp4"
)


# =========================================================
# RENDER BUTTON
# =========================================================

if st.button(
    "🎬 Genereer Smooth Glitch Video",
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
        # FRAMES
        # =================================================

        for frame_index in range(
            frames_total
        ):

            # ---------------------------------------------
            # LOOP-POSITIE
            # ---------------------------------------------

            t = (
                frame_index
                / frames_total
            )


            # ---------------------------------------------
            # Originele foto
            # ---------------------------------------------

            frame = img.copy()


            # ---------------------------------------------
            # Bewegende strepen
            # ---------------------------------------------

            for band in bands:

                y1 = band["y1"]
                y2 = band["y2"]

                stretch_width = (
                    band["stretch_width"]
                )


                # -----------------------------------------
                # Zeer vloeiende sinusbeweging
                # -----------------------------------------

                wave = (
                    np.sin(
                        (
                            t
                            * 2
                            * np.pi
                            * movement_speed
                            * band["speed"]
                        )
                        + band["phase"]
                    )
                    + 1
                ) / 2


                # Van links naar rechts
                # en terug.
                #
                # Hierdoor ontstaat geen harde reset.
                position = (
                    wave
                    * max(
                        1,
                        stretch_width - width
                    )
                )


                if band["direction"] < 0:

                    position = (
                        stretch_width
                        - width
                        - position
                    )


                position = int(
                    position
                )


                # -----------------------------------------
                # Stuk uit stretched image
                # -----------------------------------------

                stretched = band["data"]


                start = int(
                    np.clip(
                        position,
                        0,
                        max(
                            0,
                            stretch_width - width
                        )
                    )
                )


                end = start + width


                if end > stretch_width:

                    end = stretch_width

                    start = (
                        end - width
                    )


                moving_strip = stretched[
                    :,
                    start:end,
                    :
                ]


                # Veiligheid
                if moving_strip.shape[1] != width:

                    continue


                # -----------------------------------------
                # Subtiel mengen met originele foto
                # -----------------------------------------

                alpha = band["alpha"]


                original_strip = frame[
                    y1:y2,
                    :,
                    :
                ]


                mixed = (
                    original_strip.astype(
                        np.float32
                    )
                    * (1.0 - alpha)
                    +
                    moving_strip.astype(
                        np.float32
                    )
                    * alpha
                )


                frame[
                    y1:y2,
                    :,
                    :
                ] = np.clip(
                    mixed,
                    0,
                    255
                ).astype(
                    np.uint8
                )


            # =================================================
            # EXTRA SMOOTH LONG STRETCHES
            # =================================================

            # Een paar grotere lijnen bewegen door
            # het hele beeld heen.

            long_count = max(
                1,
                band_amount // 8
            )


            for j in range(
                long_count
            ):

                phase = (
                    j * 1.7
                )


                wave = (
                    np.sin(
                        (
                            t
                            * 2
                            * np.pi
                            * movement_speed
                            * 0.45
                        )
                        + phase
                    )
                    + 1
                ) / 2


                y = int(
                    (
                        (
                            j + 0.5
                        )
                        / long_count
                    )
                    * height
                )


                thickness = max(
                    1,
                    int(
                        height
                        * 0.008
                    )
                )


                y1 = max(
                    0,
                    y - thickness
                )


                y2 = min(
                    height,
                    y + thickness
                )


                # Horizontale shift
                shift = int(
                    (
                        wave - 0.5
                    )
                    * width
                    * 0.45
                )


                strip = frame[
                    y1:y2,
                    :,
                    :
                ]


                shifted = np.roll(
                    strip,
                    shift,
                    axis=1
                )


                # Heel subtiel mengen
                frame[
                    y1:y2,
                    :,
                    :
                ] = (
                    strip.astype(
                        np.float32
                    )
                    * 0.35
                    +
                    shifted.astype(
                        np.float32
                    )
                    * 0.65
                ).astype(
                    np.uint8
                )


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
                    f"〰️ Smooth frames renderen: "
                    f"{frame_index + 1} / "
                    f"{frames_total}"
                )
            )


            status.write(
                f"Frame {frame_index + 1} van {frames_total}"
            )


        # =====================================================
        # FFMPEG AFRONDEN
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
        # RESULTAAT
        # =====================================================

        if not os.path.exists(
            output_path
        ):

            st.error(
                "❌ Het MP4-bestand is niet gevonden."
            )

            st.stop()


        progress.progress(
            1.0,
            text="✅ Klaar!"
        )

        status.empty()


        file_size = os.path.getsize(
            output_path
        )


        st.success(
            "🎉 Smooth glitch-video is klaar!"
        )


        st.write(
            f"Bestandsgrootte: "
            f"**{file_size / 1024 / 1024:.1f} MB**"
        )


        # =====================================================
        # VIDEO PREVIEW
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
            file_name="smooth_pixel_stretch.mp4",
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
