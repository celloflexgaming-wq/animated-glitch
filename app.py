import streamlit as st
import numpy as np
from PIL import Image
import subprocess
import tempfile
import os
import shutil


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="Animated Pixel Glitch",
    page_icon="🎞️",
    layout="centered"
)

st.title("🎞️ Animated Pixel Glitch")
st.caption(
    "Maak een vloeiende pixel-stretch / glitch animatie "
    "van één foto."
)


# =========================================================
# SETTINGS
# =========================================================

uploaded_file = st.file_uploader(
    "📷 Upload je foto",
    type=["jpg", "jpeg", "png", "webp"]
)

if uploaded_file is None:
    st.info("Upload hierboven een foto om te beginnen.")
    st.stop()


st.subheader("⚙️ Instellingen")

col1, col2 = st.columns(2)

with col1:

    duration = st.selectbox(
        "Duur",
        [5, 10, 15],
        index=2
    )

    fps = st.selectbox(
        "Frames per seconde",
        [24, 30, 60],
        index=1
    )

with col2:

    max_width = st.selectbox(
        "Maximale breedte",
        [800, 1280, 1920],
        index=2
    )

    quality = st.select_slider(
        "Video kwaliteit",
        options=["Hoog", "Zeer hoog", "Maximaal"],
        value="Zeer hoog"
    )


intensity = st.slider(
    "⚡ Glitch intensiteit",
    min_value=1,
    max_value=10,
    value=6
)

motion = st.slider(
    "🌊 Bewegingssnelheid",
    min_value=1,
    max_value=10,
    value=5
)

preview = st.checkbox(
    "👁️ Toon originele foto",
    value=True
)


# =========================================================
# LOAD IMAGE
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


if preview:

    st.image(
        image,
        caption=f"Origineel · {width} × {height}",
        use_container_width=True
    )


frames_total = duration * fps


st.write(
    f"🎬 **Output:** {width} × {height} · "
    f"{fps} FPS · {duration} seconden · "
    f"{frames_total} frames"
)


# =========================================================
# CREATE GLITCH STRUCTURE
# =========================================================

rng = np.random.default_rng(82741)


# Meer intensiteit = meer banden
band_count = int(
    18 + intensity * 7
)


# Willekeurige horizontale bandgrenzen
raw_positions = np.linspace(
    0,
    height,
    band_count + 1
).astype(int)


bands = []


for i in range(band_count):

    y1 = int(raw_positions[i])
    y2 = int(raw_positions[i + 1])

    if y2 <= y1:
        continue

    band_height = y2 - y1


    # Aantal stretch-segmenten
    segment_count = int(
        rng.integers(
            1,
            max(2, 3 + intensity // 2)
        )
    )


    possible_splits = np.arange(
        1,
        width
    )


    if len(possible_splits) > segment_count - 1:

        split_points = sorted(
            rng.choice(
                possible_splits,
                size=segment_count - 1,
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


    segments = []


    for j in range(
        len(split_points) - 1
    ):

        x1 = int(
            split_points[j]
        )

        x2 = int(
            split_points[j + 1]
        )

        if x2 <= x1:
            continue


        segment_width = x2 - x1


        # Willekeurige bronkolom
        source_x = int(
            rng.integers(
                x1,
                max(x1 + 1, x2)
            )
        )


        # Verticale strook uit de originele foto
        source = img[
            y1:y2,
            source_x:source_x + 1,
            :
        ]


        # Horizontaal uitrekken
        stretched = np.repeat(
            source,
            segment_width,
            axis=1
        )


        # Elke band eigen beweging
        band_speed = float(
            rng.uniform(
                0.35,
                1.0
            )
        )


        direction = int(
            rng.choice(
                [-1, 1]
            )
        )


        phase = float(
            rng.random()
        )


        segments.append(
            {
                "x1": x1,
                "x2": x2,
                "data": stretched,
                "speed": band_speed,
                "direction": direction,
                "phase": phase
            }
        )


    bands.append(
        {
            "y1": y1,
            "y2": y2,
            "segments": segments
        }
    )


# =========================================================
# QUALITY SETTINGS
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
    prefix="pixel_glitch_"
)

output_path = os.path.join(
    temp_dir,
    "animated_pixel_glitch.mp4"
)


# =========================================================
# START
# =========================================================

if st.button(
    "🎬 Genereer MP4",
    type="primary",
    use_container_width=True
):

    progress = st.progress(
        0,
        text="Video voorbereiden..."
    )

    status = st.empty()


    ffmpeg_command = [

        "ffmpeg",

        "-y",

        # Raw RGB input
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

        # H.264
        "-c:v",
        "libx264",

        "-preset",
        preset,

        "-crf",
        str(crf),

        "-pix_fmt",
        "yuv420p",

        # Web-friendly MP4
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
        # GENERATE FRAMES
        # =================================================

        for frame_index in range(
            frames_total
        ):

            # 0 -> bijna 1
            t = (
                frame_index
                / frames_total
            )


            # Begin met origineel
            frame = img.copy()


            # ---------------------------------------------
            # Pixel stretch bands
            # ---------------------------------------------

            for band in bands:

                y1 = band["y1"]
                y2 = band["y2"]


                for segment in band["segments"]:

                    x1 = segment["x1"]
                    x2 = segment["x2"]

                    segment_width = (
                        x2 - x1
                    )


                    # Periodieke beweging.
                    # Hierdoor springt de animatie niet
                    # hard terug bij de loop.
                    cycles = (
                        0.5
                        + motion * segment["speed"] * 0.35
                    )


                    phase = (
                        t * cycles
                        + segment["phase"]
                    )


                    pixel_shift = int(
                        round(
                            phase
                            * segment_width
                        )
                    )


                    if segment["direction"] < 0:

                        pixel_shift *= -1


                    shifted = np.roll(
                        segment["data"],
                        pixel_shift,
                        axis=1
                    )


                    frame[
                        y1:y2,
                        x1:x2,
                        :
                    ] = shifted


            # ---------------------------------------------
            # Extra micro-glitch
            # ---------------------------------------------

            # Een paar kleine horizontale stroken
            # verschuiven subtiel mee.

            micro_count = max(
                1,
                intensity // 3
            )


            for _ in range(
                micro_count
            ):

                band_height = int(
                    rng.integers(
                        max(1, height // 300),
                        max(2, height // 80)
                    )
                )


                y = int(
                    rng.integers(
                        0,
                        max(1, height - band_height)
                    )
                )


                shift = int(
                    np.sin(
                        t
                        * np.pi
                        * 2
                        * rng.uniform(
                            0.5,
                            2.0
                        )
                    )
                    * width
                    * 0.08
                )


                frame[
                    y:y + band_height,
                    :
                ] = np.roll(
                    frame[
                        y:y + band_height,
                        :
                    ],
                    shift,
                    axis=1
                )


            # ---------------------------------------------
            # Send directly to FFmpeg
            # ---------------------------------------------

            process.stdin.write(
                frame.tobytes()
            )


            # ---------------------------------------------
            # Progress
            # ---------------------------------------------

            percent = (
                frame_index + 1
            ) / frames_total


            progress.progress(
                percent,
                text=(
                    f"🎞️ Renderen: "
                    f"{frame_index + 1} / "
                    f"{frames_total}"
                )
            )


            status.write(
                f"Frame {frame_index + 1} van "
                f"{frames_total}"
            )


        # =================================================
        # FINISH FFMPEG
        # =================================================

        process.stdin.close()

        stderr = process.stderr.read().decode(
            "utf-8",
            errors="replace"
        )

        return_code = process.wait()


        # =================================================
        # CHECK RESULT
        # =================================================

        if return_code != 0:

            st.error(
                "❌ FFmpeg kon de video niet maken."
            )

            st.code(
                stderr[-6000:]
            )

            st.stop()


        if not os.path.exists(
            output_path
        ):

            st.error(
                "❌ FFmpeg is klaar, maar "
                "het MP4-bestand ontbreekt."
            )

            st.stop()


        # =================================================
        # SUCCESS
        # =================================================

        progress.progress(
            1.0,
            text="✅ Video klaar!"
        )

        status.empty()


        file_size = os.path.getsize(
            output_path
        )


        st.success(
            "🎉 Je glitch-video is klaar!"
        )


        st.write(
            f"Bestandsgrootte: "
            f"**{file_size / 1024 / 1024:.1f} MB**"
        )


        # Preview
        with open(
            output_path,
            "rb"
        ) as f:

            video_data = f.read()


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


    except BrokenPipeError:

        st.error(
            "❌ FFmpeg stopte onverwacht tijdens "
            "het renderen."
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
            "❌ Er ging iets mis tijdens "
            "het renderen."
        )

        st.exception(e)


    finally:

        # FFmpeg opruimen
        if process is not None:

            try:

                if process.poll() is None:
                    process.kill()

            except Exception:
                pass


        # Tijdelijke bestanden verwijderen
        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )
