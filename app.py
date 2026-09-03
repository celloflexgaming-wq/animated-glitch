import streamlit as st
import numpy as np
from PIL import Image
import subprocess
import tempfile
import os
import math
import io
import shutil
import gc


# ============================================================
# 1. STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="Ultimate Motion Glitch Studio",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.stButton > button {
    width: 100%;
    border-radius: 6px;
    font-weight: bold;
    height: 3em;
    transition: 0.2s;
}

.stButton > button:hover {
    transform: scale(1.02);
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# 2. VEILIGHEID / LIMITS
# ============================================================

# Voorkomt dat extreem grote afbeeldingen het geheugen slopen.
MAX_INPUT_PIXELS = 20_000_000

# Maximale afmeting voor "Origineel".
MAX_ORIGINAL_DIMENSION = 4096


# ============================================================
# 3. HELPERS
# ============================================================

def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def cleanup_file(path):
    """Verwijder tijdelijk bestand zonder ooit een crash te veroorzaken."""
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


def check_ffmpeg():
    """Controleer of FFmpeg beschikbaar is."""
    return shutil.which("ffmpeg") is not None


def load_image_safely(uploaded_file):
    """
    Laadt een afbeelding veilig en voorkomt extreem
    geheugenverbruik.
    """

    try:
        image = Image.open(uploaded_file)

        # Forceer daadwerkelijke decode voordat we verder gaan.
        image.load()

        image = image.convert("RGB")

        pixels = image.width * image.height

        # Te grote afbeelding automatisch verkleinen.
        if pixels > MAX_INPUT_PIXELS:

            scale = math.sqrt(
                MAX_INPUT_PIXELS / pixels
            )

            new_width = max(
                2,
                int(image.width * scale)
            )

            new_height = max(
                2,
                int(image.height * scale)
            )

            image = image.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS
            )

            st.warning(
                "⚠️ De originele foto was extreem groot. "
                f"Deze is automatisch verkleind naar "
                f"{new_width} × {new_height} om crashes te voorkomen."
            )

        return image

    except Exception as e:

        st.error(
            "❌ Deze afbeelding kon niet worden geopend."
        )

        st.caption(
            f"Technische melding: {type(e).__name__}"
        )

        return None


def prepare_output_image(
    img,
    resolution
):
    """
    Maakt de afbeelding klaar voor de gekozen output.
    Cropt naar 16:9 en schaalt met Lanczos.
    """

    try:

        if resolution == "1920x1080 (Full HD)":

            tw, th = 1920, 1080

        elif resolution == "1280x720 (HD)":

            tw, th = 1280, 720

        else:

            # Origineel, maar wel veilig begrensd.
            w = min(
                img.width,
                MAX_ORIGINAL_DIMENSION
            )

            h = min(
                img.height,
                MAX_ORIGINAL_DIMENSION
            )

            if w != img.width or h != img.height:

                scale = min(
                    w / img.width,
                    h / img.height
                )

                w = max(
                    2,
                    int(img.width * scale)
                )

                h = max(
                    2,
                    int(img.height * scale)
                )

                img = img.resize(
                    (w, h),
                    Image.Resampling.LANCZOS
                )

            # H.264 houdt van even afmetingen.
            w = w - (w % 2)
            h = h - (h % 2)

            return img.resize(
                (w, h),
                Image.Resampling.LANCZOS
            )

        # ----------------------------------------------------
        # 16:9 CROP
        # ----------------------------------------------------

        source_ratio = img.width / img.height
        target_ratio = tw / th

        if source_ratio > target_ratio:

            # Te breed -> zijkanten eraf.
            new_width = int(
                img.height * target_ratio
            )

            left = (
                img.width - new_width
            ) // 2

            img = img.crop(
                (
                    left,
                    0,
                    left + new_width,
                    img.height
                )
            )

        elif source_ratio < target_ratio:

            # Te hoog -> boven/onder eraf.
            new_height = int(
                img.width / target_ratio
            )

            top = (
                img.height - new_height
            ) // 2

            img = img.crop(
                (
                    0,
                    top,
                    img.width,
                    top + new_height
                )
            )

        # ----------------------------------------------------
        # EXACTE OUTPUT RESOLUTIE
        # ----------------------------------------------------

        img = img.resize(
            (tw, th),
            Image.Resampling.LANCZOS
        )

        return img

    except Exception:

        st.error(
            "❌ De afbeelding kon niet naar de "
            "gekozen resolutie worden omgezet."
        )

        return None


# ============================================================
# 4. CLASSIC GLITCH ENGINE
# ============================================================

def generate_classic_glitch_data(
    width,
    height,
    bands_count,
    complexity_max,
    seed=42
):

    rng = np.random.default_rng(
        int(seed)
    )

    # Veilig begrenzen.
    bands_count = max(
        1,
        min(
            int(bands_count),
            height
        )
    )

    complexity_max = max(
        1,
        min(
            int(complexity_max),
            10
        )
    )

    band_edges = np.linspace(
        0,
        height,
        bands_count + 1
    ).astype(int)

    bands = []

    for i in range(bands_count):

        y1 = int(band_edges[i])
        y2 = int(band_edges[i + 1])

        if y2 <= y1:
            continue

        # Segmenten mogen nooit groter zijn dan de breedte.
        max_segments = min(
            complexity_max,
            width
        )

        num_segments = int(
            rng.integers(
                1,
                max_segments + 1
            )
        )

        if num_segments == 1:

            splits = [0, width]

        else:

            possible = np.arange(
                1,
                width
            )

            if len(possible) < num_segments - 1:

                num_segments = len(possible) + 1

            if num_segments <= 1:

                splits = [0, width]

            else:

                split_points = sorted(
                    rng.choice(
                        possible,
                        size=num_segments - 1,
                        replace=False
                    ).tolist()
                )

                splits = (
                    [0]
                    + split_points
                    + [width]
                )

        segments = []

        for j in range(
            len(splits) - 1
        ):

            x1 = int(splits[j])
            x2 = int(splits[j + 1])

            if x2 <= x1:
                continue

            sample_x = int(
                rng.integers(
                    x1,
                    x2
                )
            )

            segments.append(
                {
                    "x1": x1,
                    "x2": x2,
                    "sample_x": sample_x
                }
            )

        bands.append(
            {
                "y1": y1,
                "y2": y2,
                "segments": segments,
                "direction": int(
                    rng.choice([-1, 1])
                ),
                "cycles": int(
                    rng.integers(1, 4)
                ),
                "phase": float(
                    rng.random() * 2 * math.pi
                )
            }
        )

    return bands


# ============================================================
# 5. REPONENEN GRID ENGINE
# ============================================================

def generate_repponen_grid_data(
    width,
    height,
    num_cols,
    base_rows,
    chaos_factor,
    brightness_var,
    seed=42
):

    rng = np.random.default_rng(
        int(seed)
    )

    num_cols = max(
        2,
        min(
            int(num_cols),
            width
        )
    )

    base_rows = max(
        2,
        min(
            int(base_rows),
            height
        )
    )

    chaos_factor = float(
        np.clip(
            chaos_factor,
            0.0,
            0.8
        )
    )

    brightness_var = float(
        np.clip(
            brightness_var,
            0.0,
            0.5
        )
    )

    blocks = []

    # --------------------------------------------------------
    # KOLOMMEN
    # --------------------------------------------------------

    col_edges = [0]
    curr_x = 0

    average_width = max(
        1,
        width / num_cols
    )

    safety_counter = 0
    max_iterations = width + 10

    while (
        curr_x < width
        and safety_counter < max_iterations
    ):

        step = max(
            5,
            int(
                rng.normal(
                    average_width,
                    average_width * chaos_factor
                )
            )
        )

        curr_x += step

        if curr_x >= width - 5:
            break

        col_edges.append(
            curr_x
        )

        safety_counter += 1

    col_edges.append(width)

    # --------------------------------------------------------
    # BLOKKEN
    # --------------------------------------------------------

    for i in range(
        len(col_edges) - 1
    ):

        x1 = int(col_edges[i])
        x2 = int(col_edges[i + 1])

        if x2 <= x1:
            continue

        col_width = x2 - x1

        target_rows = max(
            2,
            int(
                base_rows
                * rng.uniform(
                    1.0 - chaos_factor,
                    1.0 + chaos_factor
                )
            )
        )

        average_height = max(
            1,
            height / target_rows
        )

        row_edges = [0]
        curr_y = 0

        safety_counter = 0

        while (
            curr_y < height
            and safety_counter < height + 10
        ):

            step = max(
                2,
                int(
                    rng.normal(
                        average_height,
                        average_height
                        * chaos_factor
                    )
                )
            )

            curr_y += step

            if curr_y >= height - 2:
                break

            row_edges.append(
                curr_y
            )

            safety_counter += 1

        row_edges.append(height)

        for j in range(
            len(row_edges) - 1
        ):

            y1 = int(row_edges[j])
            y2 = int(row_edges[j + 1])

            if y2 <= y1:
                continue

            sample_x = int(
                rng.integers(
                    x1,
                    x2
                )
            )

            if brightness_var > 0:

                brightness_value = rng.uniform(
                    1.0 - brightness_var,
                    1.0 + brightness_var
                )

            else:

                brightness_value = 1.0

            blocks.append(
                {
                    "x1": x1,
                    "x2": x2,
                    "y1": y1,
                    "y2": y2,
                    "sample_x": sample_x,
                    "brightness": float(
                        brightness_value
                    ),
                    "phase": float(
                        rng.random() * 2 * math.pi
                    ),
                    "speed": float(
                        rng.uniform(0.1, 1.0)
                        * rng.choice([-1, 1])
                    )
                }
            )

    return blocks


# ============================================================
# 6. STATIC CLASSIC RENDER
# ============================================================

def render_static_classic(
    img_arr,
    bands
):

    h, w, _ = img_arr.shape

    out_arr = np.empty_like(
        img_arr
    )

    for band in bands:

        y1 = band["y1"]
        y2 = band["y2"]

        for seg in band["segments"]:

            x1 = seg["x1"]
            x2 = seg["x2"]
            sx = seg["sample_x"]

            src = img_arr[
                y1:y2,
                sx:sx + 1,
                :
            ]

            out_arr[
                y1:y2,
                x1:x2,
                :
            ] = np.repeat(
                src,
                x2 - x1,
                axis=1
            )

    return out_arr


# ============================================================
# 7. STATIC GRID RENDER
# ============================================================

def render_static_grid(
    img_arr,
    blocks
):

    out_arr = np.empty_like(
        img_arr
    )

    for b in blocks:

        x1 = b["x1"]
        x2 = b["x2"]
        y1 = b["y1"]
        y2 = b["y2"]

        sx = int(
            np.clip(
                b["sample_x"],
                x1,
                x2 - 1
            )
        )

        bw = x2 - x1

        stretched = np.repeat(
            img_arr[
                y1:y2,
                sx:sx + 1,
                :
            ],
            bw,
            axis=1
        )

        if b["brightness"] != 1.0:

            stretched = np.clip(
                stretched.astype(np.float32)
                * b["brightness"],
                0,
                255
            ).astype(np.uint8)

        out_arr[
            y1:y2,
            x1:x2,
            :
        ] = stretched

    return out_arr


# ============================================================
# 8. FFMPEG VIDEO RENDER
# ============================================================

def render_video(
    img_arr,
    stijl,
    bands_count,
    complexity,
    num_cols,
    base_rows,
    chaos,
    brightness,
    seed_val,
    duration,
    fps,
    anim_speed,
    crf,
    preset,
    progress_bar
):

    h, w, _ = img_arr.shape

    total_frames = int(
        duration * fps
    )

    if total_frames <= 0:
        raise ValueError(
            "Het aantal frames is ongeldig."
        )

    if not check_ffmpeg():

        raise RuntimeError(
            "FFmpeg is niet geïnstalleerd "
            "of niet beschikbaar in deze omgeving."
        )

    output_path = None
    proc = None

    try:

        # ----------------------------------------------------
        # OUTPUT FILE
        # ----------------------------------------------------

        tmp = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".mp4"
        )

        output_path = tmp.name
        tmp.close()

        # ----------------------------------------------------
        # FFMPEG COMMAND
        # ----------------------------------------------------

        cmd = [
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
            f"{w}x{h}",

            "-r",
            str(fps),

            "-i",
            "-",

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

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )

        # ----------------------------------------------------
        # CLASSIC VOORBEREIDEN
        # ----------------------------------------------------

        bands = None
        pre_rows = None

        if stijl == "Classic Glitch (Vloeiend)":

            bands = generate_classic_glitch_data(
                w,
                h,
                bands_count,
                complexity,
                seed_val
            )

            pre_rows = []

            for b in bands:

                band_height = (
                    b["y2"] - b["y1"]
                )

                row = np.empty(
                    (
                        band_height,
                        w,
                        3
                    ),
                    dtype=np.uint8
                )

                # Alle segmenten vullen.
                for seg in b["segments"]:

                    x1 = seg["x1"]
                    x2 = seg["x2"]
                    sx = seg["sample_x"]

                    src = img_arr[
                        b["y1"]:b["y2"],
                        sx:sx + 1,
                        :
                    ]

                    row[
                        :,
                        x1:x2,
                        :
                    ] = np.repeat(
                        src,
                        x2 - x1,
                        axis=1
                    )

                pre_rows.append(
                    row
                )

        # ----------------------------------------------------
        # GRID VOORBEREIDEN
        # ----------------------------------------------------

        else:

            blocks = generate_repponen_grid_data(
                w,
                h,
                num_cols,
                base_rows,
                chaos,
                brightness,
                seed_val
            )

        # ----------------------------------------------------
        # FRAMES
        # ----------------------------------------------------

        for frame_number in range(
            total_frames
        ):

            t = (
                frame_number / fps
            )

            # Altijd volledig gevuld.
            f_out = np.empty_like(
                img_arr
            )

            # =================================================
            # CLASSIC
            # =================================================

            if stijl == "Classic Glitch (Vloeiend)":

                for idx, b in enumerate(bands):

                    # Soepele beweging.
                    angle = (
                        2
                        * math.pi
                        * (
                            b["cycles"]
                            * t
                            / duration
                        )
                        + b["phase"]
                    )

                    movement = math.sin(
                        angle
                    )

                    shift = int(
                        movement
                        * (
                            w * 0.5
                        )
                        * b["direction"]
                        * anim_speed
                    )

                    f_out[
                        b["y1"]:b["y2"],
                        :,
                        :
                    ] = np.roll(
                        pre_rows[idx],
                        shift,
                        axis=1
                    )

            # =================================================
            # REPONENEN GRID
            # =================================================

            else:

                for b in blocks:

                    x1 = b["x1"]
                    x2 = b["x2"]
                    y1 = b["y1"]
                    y2 = b["y2"]

                    bw = x2 - x1

                    if bw <= 0:
                        continue

                    offset = int(
                        math.sin(
                            t
                            * anim_speed
                            * b["speed"]
                            + b["phase"]
                        )
                        * (
                            bw / 2.5
                        )
                    )

                    sx = int(
                        np.clip(
                            b["sample_x"]
                            + offset,
                            x1,
                            x2 - 1
                        )
                    )

                    stretched = np.repeat(
                        img_arr[
                            y1:y2,
                            sx:sx + 1,
                            :
                        ],
                        bw,
                        axis=1
                    )

                    if b["brightness"] != 1.0:

                        stretched = np.clip(
                            stretched.astype(
                                np.float32
                            )
                            * b["brightness"],
                            0,
                            255
                        ).astype(
                            np.uint8
                        )

                    f_out[
                        y1:y2,
                        x1:x2,
                        :
                    ] = stretched

            # ------------------------------------------------
            # NAAR FFMPEG
            # ------------------------------------------------

            try:

                proc.stdin.write(
                    f_out.tobytes()
                )

            except BrokenPipeError:

                # FFmpeg is gestopt.
                stderr_data = b""

                try:
                    stderr_data = (
                        proc.stderr.read()
                    )
                except Exception:
                    pass

                message = (
                    stderr_data.decode(
                        "utf-8",
                        errors="replace"
                    )
                    if stderr_data
                    else "FFmpeg stopte onverwacht."
                )

                raise RuntimeError(
                    message
                )

            # ------------------------------------------------
            # PROGRESS
            # ------------------------------------------------

            if (
                frame_number % max(
                    1,
                    fps // 2
                ) == 0
            ):

                progress_bar.progress(
                    min(
                        1.0,
                        (
                            frame_number + 1
                        )
                        / total_frames
                    )
                )

        # ----------------------------------------------------
        # INPUT SLUITEN
        # ----------------------------------------------------

        try:
            proc.stdin.close()
        except Exception:
            pass

        # ----------------------------------------------------
        # FFmpeg AFWACHTEN
        # ----------------------------------------------------

        return_code = proc.wait()

        stderr_data = b""

        try:
            stderr_data = (
                proc.stderr.read()
            )
        except Exception:
            pass

        if return_code != 0:

            error_text = stderr_data.decode(
                "utf-8",
                errors="replace"
            )

            raise RuntimeError(
                error_text
                or "FFmpeg kon de video niet renderen."
            )

        # ----------------------------------------------------
        # CONTROLEREN OF BESTAND BESTAAT
        # ----------------------------------------------------

        if (
            not output_path
            or not os.path.exists(output_path)
        ):

            raise RuntimeError(
                "FFmpeg heeft geen MP4-bestand geproduceerd."
            )

        file_size = os.path.getsize(
            output_path
        )

        if file_size < 1000:

            raise RuntimeError(
                "Het gegenereerde videobestand "
                "is ongeldig of leeg."
            )

        progress_bar.progress(1.0)

        return output_path

    except Exception:

        if proc is not None:

            try:
                if proc.poll() is None:
                    proc.kill()
            except Exception:
                pass

            try:
                proc.stdin.close()
            except Exception:
                pass

        cleanup_file(
            output_path
        )

        raise

    finally:

        gc.collect()


# ============================================================
# 9. SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🎛️ Project Setup")

    uploaded = st.file_uploader(
        "1. Media",
        type=[
            "jpg",
            "jpeg",
            "png",
            "webp"
        ]
    )

    stijl = st.selectbox(
        "2. Engine",
        [
            "Classic Glitch (Vloeiend)",
            "Repponen Grid (Blokken)"
        ]
    )

    modus = st.radio(
        "3. Output Type",
        [
            "🖼️ Statisch Beeld",
            "🎥 Motion (MP4)"
        ]
    )


# ============================================================
# 10. HOOFDAPP
# ============================================================

if not uploaded:

    st.info(
        "👋 Sleep een afbeelding in het uploadveld "
        "om te beginnen."
    )

    st.stop()


# ============================================================
# 11. AFBEELDING LADEN
# ============================================================

img = load_image_safely(
    uploaded
)

if img is None:
    st.stop()


# ============================================================
# 12. COLUMNS
# ============================================================

col_controls, col_canvas = st.columns(
    [1.2, 2],
    gap="large"
)


# ============================================================
# 13. CONTROLS
# ============================================================

with col_controls:

    tab_design, tab_motion, tab_render = st.tabs(
        [
            "🎨 Vormgeving",
            "🎞️ Motion",
            "⚙️ Export"
        ]
    )

    # --------------------------------------------------------
    # DESIGN
    # --------------------------------------------------------

    with tab_design:

        st.subheader(
            "Look & Feel"
        )

        if stijl == "Classic Glitch (Vloeiend)":

            bands_count = st.slider(
                "Glitch Dichtheid",
                10,
                300,
                100
            )

            complexity = st.slider(
                "Segment Complexiteit",
                1,
                10,
                4
            )

        else:

            num_cols = st.slider(
                "Verticale Kolommen",
                2,
                150,
                40
            )

            base_rows = st.slider(
                "Horizontale Rijen",
                10,
                300,
                100
            )

            chaos = st.slider(
                "Asymmetrie (Chaos)",
                0.0,
                0.8,
                0.35,
                step=0.05
            )

            brightness = st.slider(
                "Blok Contrast",
                0.0,
                0.5,
                0.15,
                step=0.05
            )

        seed_val = st.number_input(
            "Variatie Seed",
            value=42,
            step=1
        )

    # --------------------------------------------------------
    # MOTION
    # --------------------------------------------------------

    with tab_motion:

        if modus == "🎥 Motion (MP4)":

            st.subheader(
                "Animatie Dynamiek"
            )

            anim_speed = st.slider(
                "Globale Snelheid",
                0.05,
                5.0,
                1.0,
                step=0.05
            )

            duration = st.select_slider(
                "Duur (seconden)",
                options=[
                    5,
                    10,
                    15,
                    30,
                    45,
                    60
                ],
                value=10
            )

        else:

            st.info(
                "Schakel naar Motion (MP4) "
                "voor animatie-instellingen."
            )

    # --------------------------------------------------------
    # EXPORT
    # --------------------------------------------------------

    with tab_render:

        st.subheader(
            "Output Kwaliteit"
        )

        resolutie = st.selectbox(
            "Resolutie",
            [
                "Origineel",
                "1920x1080 (Full HD)",
                "1280x720 (HD)"
            ],
            index=1
        )

        if modus == "🎥 Motion (MP4)":

            fps = st.selectbox(
                "Framerate",
                [
                    24,
                    30,
                    60
                ],
                index=1
            )

            quality = st.selectbox(
                "Videokwaliteit",
                [
                    "💎 Maximale kwaliteit",
                    "🔥 Zeer hoge kwaliteit",
                    "⚡ Sneller renderen"
                ],
                index=0
            )

            if quality == "💎 Maximale kwaliteit":

                crf = 12
                preset = "slow"

            elif quality == "🔥 Zeer hoge kwaliteit":

                crf = 16
                preset = "medium"

            else:

                crf = 20
                preset = "fast"

            st.caption(
                f"H.264 • CRF {crf} • preset {preset}"
            )

        render_btn = st.button(
            "🚀 Start Render",
            type="primary"
        )


# ============================================================
# 14. CANVAS
# ============================================================

with col_canvas:

    with st.expander(
        "📸 Bekijk bronbestand",
        expanded=False
    ):

        st.image(
            img,
            use_container_width=True
        )

    if render_btn:

        # ----------------------------------------------------
        # FFmpeg CHECK
        # ----------------------------------------------------

        if modus == "🎥 Motion (MP4)":

            if not check_ffmpeg():

                st.error(
                    "❌ FFmpeg is niet beschikbaar. "
                    "Controleer of `ffmpeg` in packages.txt staat."
                )

                st.stop()

        # ----------------------------------------------------
        # OUTPUT IMAGE MAKEN
        # ----------------------------------------------------

        with st.spinner(
            "Afbeelding voorbereiden..."
        ):

            target_img = prepare_output_image(
                img,
                resolutie
            )

        if target_img is None:
            st.stop()

        try:

            # ------------------------------------------------
            # NUMPY
            # ------------------------------------------------

            img_arr = np.asarray(
                target_img,
                dtype=np.uint8
            )

            h, w, _ = img_arr.shape

            st.write(
                f"**Output:** {w} × {h} px"
            )

            # =================================================
            # STATISCH
            # =================================================

            if modus == "🖼️ Statisch Beeld":

                with st.spinner(
                    "Glitch afbeelding maken..."
                ):

                    if stijl == "Classic Glitch (Vloeiend)":

                        bands = generate_classic_glitch_data(
                            w,
                            h,
                            bands_count,
                            complexity,
                            seed_val
                        )

                        out_arr = render_static_classic(
                            img_arr,
                            bands
                        )

                    else:

                        blocks = generate_repponen_grid_data(
                            w,
                            h,
                            num_cols,
                            base_rows,
                            chaos,
                            brightness,
                            seed_val
                        )

                        out_arr = render_static_grid(
                            img_arr,
                            blocks
                        )

                    res_img = Image.fromarray(
                        out_arr
                    )

                st.success(
                    "✅ Glitch afbeelding klaar!"
                )

                st.image(
                    res_img,
                    use_container_width=True
                )

                # --------------------------------------------
                # PNG DOWNLOAD
                # --------------------------------------------

                buf = io.BytesIO()

                res_img.save(
                    buf,
                    format="PNG",
                    optimize=True
                )

                st.download_button(
                    "⬇️ Download PNG",
                    data=buf.getvalue(),
                    file_name="glitch_export.png",
                    mime="image/png"
                )

                # Vrijgeven
                del out_arr

                gc.collect()

            # =================================================
            # VIDEO
            # =================================================

            else:

                total_frames = (
                    int(duration * fps)
                )

                st.write(
                    f"**Video:** {duration} sec • "
                    f"{fps} FPS • "
                    f"{total_frames} frames"
                )

                progress = st.progress(
                    0
                )

                output_path = None

                try:

                    output_path = render_video(
                        img_arr=img_arr,
                        stijl=stijl,
                        bands_count=bands_count
                        if stijl == "Classic Glitch (Vloeiend)"
                        else 100,
                        complexity=complexity
                        if stijl == "Classic Glitch (Vloeiend)"
                        else 4,
                        num_cols=num_cols
                        if stijl != "Classic Glitch (Vloeiend)"
                        else 40,
                        base_rows=base_rows
                        if stijl != "Classic Glitch (Vloeiend)"
                        else 100,
                        chaos=chaos
                        if stijl != "Classic Glitch (Vloeiend)"
                        else 0.35,
                        brightness=brightness
                        if stijl != "Classic Glitch (Vloeiend)"
                        else 0.15,
                        seed_val=seed_val,
                        duration=duration,
                        fps=fps,
                        anim_speed=anim_speed,
                        crf=crf,
                        preset=preset,
                        progress_bar=progress
                    )

                    # ----------------------------------------
                    # MP4 INLEZEN
                    # ----------------------------------------

                    with open(
                        output_path,
                        "rb"
                    ) as video_file:

                        video_bytes = (
                            video_file.read()
                        )

                    # ----------------------------------------
                    # RESULTAAT
                    # ----------------------------------------

                    st.success(
                        "✅ Render voltooid!"
                    )

                    st.video(
                        video_bytes
                    )

                    st.download_button(
                        "⬇️ Download MP4",
                        data=video_bytes,
                        file_name=(
                            "smooth_glitch_full_hd.mp4"
                        ),
                        mime="video/mp4"
                    )

                except MemoryError:

                    st.error(
                        "❌ Onvoldoende geheugen tijdens het renderen."
                    )

                    st.info(
                        "Probeer eerst 1280×720, "
                        "30 FPS of een kortere video."
                    )

                except BrokenPipeError:

                    st.error(
                        "❌ FFmpeg is onverwacht gestopt."
                    )

                    st.info(
                        "Probeer 1280×720 of een lagere "
                        "videokwaliteit."
                    )

                except Exception as e:

                    st.error(
                        "❌ De render is niet gelukt."
                    )

                    st.caption(
                        f"Technische fout: "
                        f"{type(e).__name__}"
                    )

                    with st.expander(
                        "🔧 Technische details"
                    ):

                        st.code(
                            str(e)
                        )

                finally:

                    # ----------------------------------------
                    # ALTIJD OPSCHONEN
                    # ----------------------------------------

                    cleanup_file(
                        output_path
                    )

                    gc.collect()

            # ----------------------------------------------
            # GEHEUGEN VRIJGEVEN
            # ----------------------------------------------

            del img_arr
            del target_img

            gc.collect()

        except MemoryError:

            st.error(
                "❌ De afbeelding is te groot voor "
                "het beschikbare geheugen."
            )

            st.info(
                "Gebruik 1920×1080 of 1280×720 "
                "in plaats van 'Origineel'."
            )

        except Exception as e:

            st.error(
                "❌ Er ging iets mis tijdens het renderen."
            )

            st.caption(
                f"Technische fout: "
                f"{type(e).__name__}"
            )

            with st.expander(
                "🔧 Technische details"
            ):

                st.code(
                    str(e)
                )
