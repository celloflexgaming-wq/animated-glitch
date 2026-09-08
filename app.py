import streamlit as st
import numpy as np
from PIL import Image, ImageFile
import subprocess
import tempfile
import os
import math
import io
import shutil
import gc
import time

# ============================================================
# 1. STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="Ultimate Motion Glitch Studio",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stButton > button {
        width: 100%;
        border-radius: 6px;
        font-weight: bold;
        height: 3em;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 2. VEILIGE LIMITS
# ============================================================

MAX_UPLOAD_MB = 30
MAX_INPUT_PIXELS = 16_000_000
MAX_INPUT_DIMENSION = 4096
MAX_VIDEO_WIDTH = 1920
MAX_VIDEO_HEIGHT = 1080
MAX_VIDEO_DURATION = 30
MAX_VIDEO_FPS = 30
MAX_VIDEO_FRAMES = MAX_VIDEO_DURATION * MAX_VIDEO_FPS

# ============================================================
# 3. HELPERS
# ============================================================

def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default

def cleanup_file(path):
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass

def check_ffmpeg():
    return shutil.which("ffmpeg") is not None

def get_ffmpeg_version():
    if not check_ffmpeg():
        return None
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
        )
        return result.stdout.splitlines()[0] if result.stdout else "FFmpeg gevonden"
    except Exception:
        return "FFmpeg gevonden"

def image_from_uploaded_file(uploaded_file):
    try:
        file_size_mb = uploaded_file.size / (1024 * 1024)
        if file_size_mb > MAX_UPLOAD_MB:
            st.error(f"❌ Bestand is te groot ({file_size_mb:.1f} MB). Maximum: {MAX_UPLOAD_MB} MB.")
            return None

        uploaded_file.seek(0)
        ImageFile.LOAD_TRUNCATED_IMAGES = False
        image = Image.open(uploaded_file)
        image.load()
        image = image.convert("RGB")
        pixels = image.width * image.height

        if pixels > MAX_INPUT_PIXELS:
            scale = math.sqrt(MAX_INPUT_PIXELS / pixels)
            new_width = max(2, int(image.width * scale))
            new_height = max(2, int(image.height * scale))
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            st.warning(f"⚠️ Grote afbeelding automatisch verkleind naar {new_width} × {new_height} px.")

        if image.width > MAX_INPUT_DIMENSION or image.height > MAX_INPUT_DIMENSION:
            scale = min(MAX_INPUT_DIMENSION / image.width, MAX_INPUT_DIMENSION / image.height)
            new_width = max(2, int(image.width * scale))
            new_height = max(2, int(image.height * scale))
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        return image
    except Exception as e:
        st.error("❌ Deze afbeelding kon niet worden geopend.")
        st.caption(f"Technische melding: {type(e).__name__}: {e}")
        return None

def prepare_output_image(img, resolution, for_video=False):
    try:
        if resolution == "1920x1080 (Full HD)":
            tw, th = 1920, 1080
        elif resolution == "1280x720 (HD)":
            tw, th = 1280, 720
        else:
            if for_video:
                scale = min(1.0, MAX_VIDEO_WIDTH / img.width, MAX_VIDEO_HEIGHT / img.height)
                w = max(2, int(img.width * scale))
                h = max(2, int(img.height * scale))
                w -= w % 2
                h -= h % 2
                return img.resize((max(2, w), max(2, h)), Image.Resampling.LANCZOS)
            
            w = min(img.width, MAX_INPUT_DIMENSION)
            h = min(img.height, MAX_INPUT_DIMENSION)
            if w != img.width or h != img.height:
                scale = min(w / img.width, h / img.height)
                w = max(2, int(img.width * scale))
                h = max(2, int(img.height * scale))
                img = img.resize((w, h), Image.Resampling.LANCZOS)
            
            w -= w % 2
            h -= h % 2
            return img.resize((max(2, w), max(2, h)), Image.Resampling.LANCZOS)

        source_ratio = img.width / img.height
        target_ratio = tw / th

        if source_ratio > target_ratio:
            new_width = int(img.height * target_ratio)
            left = (img.width - new_width) // 2
            img = img.crop((left, 0, left + new_width, img.height))
        elif source_ratio < target_ratio:
            new_height = int(img.width / target_ratio)
            top = (img.height - new_height) // 2
            img = img.crop((0, top, img.width, top + new_height))

        return img.resize((tw, th), Image.Resampling.LANCZOS)
    except Exception as e:
        st.error("❌ De afbeelding kon niet worden voorbereid.")
        st.caption(f"Technische melding: {type(e).__name__}: {e}")
        return None

# ============================================================
# 4. CLASSIC GLITCH ENGINE
# ============================================================

def generate_classic_glitch_data(width, height, bands_count, complexity_max, seed=42):
    rng = np.random.default_rng(safe_int(seed, 42))
    bands_count = max(1, min(safe_int(bands_count, 100), height))
    complexity_max = max(1, min(safe_int(complexity_max, 4), 10))
    band_edges = np.linspace(0, height, bands_count + 1).astype(int)
    bands = []

    for i in range(bands_count):
        y1 = int(band_edges[i])
        y2 = int(band_edges[i + 1])
        if y2 <= y1:
            continue

        max_segments = min(complexity_max, width)
        num_segments = int(rng.integers(1, max_segments + 1))

        if num_segments <= 1:
            splits = [0, width]
        else:
            possible = np.arange(1, width)
            if len(possible) < num_segments - 1:
                num_segments = len(possible) + 1
            if num_segments <= 1:
                splits = [0, width]
            else:
                split_points = sorted(rng.choice(possible, size=num_segments - 1, replace=False).tolist())
                splits = [0] + split_points + [width]

        segments = []
        for j in range(len(splits) - 1):
            x1 = int(splits[j])
            x2 = int(splits[j + 1])
            if x2 <= x1:
                continue
            sample_x = int(rng.integers(x1, x2))
            segments.append({"x1": x1, "x2": x2, "sample_x": sample_x})

        bands.append({
            "y1": y1,
            "y2": y2,
            "segments": segments,
            "direction": int(rng.choice([-1, 1])),
            "cycles": int(rng.integers(1, 4)),
            "phase": float(rng.random() * 2 * math.pi),
        })
    return bands

def render_static_classic(img_arr, bands):
    out_arr = np.empty_like(img_arr)
    np.copyto(out_arr, img_arr)
    for band in bands:
        y1 = band["y1"]
        y2 = band["y2"]
        for seg in band["segments"]:
            x1 = seg["x1"]
            x2 = seg["x2"]
            sx = seg["sample_x"]
            src = img_arr[y1:y2, sx:sx + 1, :]
            out_arr[y1:y2, x1:x2, :] = src
    return out_arr

# ============================================================
# 5. REPONENEN GRID ENGINE
# ============================================================

def generate_repponen_grid_data(width, height, num_cols, base_rows, chaos_factor, brightness_var, seed=42):
    rng = np.random.default_rng(safe_int(seed, 42))
    num_cols = max(2, min(safe_int(num_cols, 40), width))
    base_rows = max(2, min(safe_int(base_rows, 100), height))
    chaos_factor = float(np.clip(chaos_factor, 0.0, 0.8))
    brightness_var = float(np.clip(brightness_var, 0.0, 0.5))
    blocks = []
    base_col_width = width / num_cols
    col_edges = [0]

    for i in range(1, num_cols):
        jitter = rng.normal(0, base_col_width * chaos_factor * 0.35)
        x = int(round(i * base_col_width + jitter))
        x = max(col_edges[-1] + 1, x)
        x = min(width - (num_cols - i), x)
        col_edges.append(x)
    col_edges.append(width)

    for i in range(len(col_edges) - 1):
        x1 = int(col_edges[i])
        x2 = int(col_edges[i + 1])
        if x2 <= x1:
            continue
        
        target_rows = max(2, int(base_rows * rng.uniform(1.0 - chaos_factor, 1.0 + chaos_factor)))
        target_rows = min(target_rows, height)
        base_height = height / target_rows
        row_edges = [0]

        for j in range(1, target_rows):
            jitter = rng.normal(0, base_height * chaos_factor * 0.35)
            y = int(round(j * base_height + jitter))
            y = max(row_edges[-1] + 1, y)
            y = min(height - (target_rows - j), y)
            row_edges.append(y)
        row_edges.append(height)

        for j in range(len(row_edges) - 1):
            y1 = int(row_edges[j])
            y2 = int(row_edges[j + 1])
            if y2 <= y1:
                continue
            sample_x = int(rng.integers(x1, x2))
            brightness_value = rng.uniform(1.0 - brightness_var, 1.0 + brightness_var) if brightness_var > 0 else 1.0

            blocks.append({
                "x1": x1,
                "x2": x2,
                "y1": y1,
                "y2": y2,
                "sample_x": sample_x,
                "brightness": float(brightness_value),
                "phase": float(rng.random() * 2 * math.pi),
                "speed": float(rng.uniform(0.1, 1.0) * rng.choice([-1, 1])),
            })
    return blocks

def render_static_grid(img_arr, blocks):
    out_arr = np.empty_like(img_arr)
    np.copyto(out_arr, img_arr)
    for b in blocks:
        x1, x2, y1, y2 = b["x1"], b["x2"], b["y1"], b["y2"]
        sx = int(np.clip(b["sample_x"], x1, x2 - 1))
        bw = x2 - x1
        if bw <= 0:
            continue

        src = img_arr[y1:y2, sx:sx + 1, :]
        block = np.broadcast_to(src, (y2 - y1, bw, 3))

        if b["brightness"] != 1.0:
            block = np.clip(block.astype(np.float32) * b["brightness"], 0, 255).astype(np.uint8)
        out_arr[y1:y2, x1:x2, :] = block

    return out_arr

# ============================================================
# 6. VIDEO RENDER
# ============================================================

def render_video(img_arr, stijl, bands_count, complexity, num_cols, base_rows, chaos, brightness, seed_val, duration, fps, anim_speed, crf, preset, progress_bar):
    h, w, _ = img_arr.shape
    fps = max(1, min(safe_int(fps, 30), MAX_VIDEO_FPS))
    duration = max(1, min(safe_int(duration, 10), MAX_VIDEO_DURATION))
    total_frames = min(duration * fps, MAX_VIDEO_FRAMES)

    if total_frames <= 0:
        raise ValueError("Het aantal frames is ongeldig.")
    if w > MAX_VIDEO_WIDTH or h > MAX_VIDEO_HEIGHT:
        raise ValueError(f"Videoresolutie {w}×{h} is te groot. Gebruik maximaal 1920×1080.")
    if not check_ffmpeg():
        raise RuntimeError("FFmpeg is niet geïnstalleerd of niet beschikbaar.")

    output_path = None
    proc = None

    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        output_path = tmp.name
        tmp.close()

        cmd = [
            "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-vcodec", "rawvideo",
            "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
            "-an", "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", output_path
        ]

        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )

        if stijl == "Classic Glitch (Vloeiend)":
            bands = generate_classic_glitch_data(w, h, bands_count, complexity, seed_val)
            pre_rows = []
            for b in bands:
                band_height = b["y2"] - b["y1"]
                row = np.empty((band_height, w, 3), dtype=np.uint8)
                row[:] = img_arr[b["y1"]:b["y2"], :, :]
                for seg in b["segments"]:
                    x1, x2, sx = seg["x1"], seg["x2"], seg["sample_x"]
                    src = img_arr[b["y1"]:b["y2"], sx:sx + 1, :]
                    row[:, x1:x2, :] = src
                pre_rows.append(row)
        else:
            blocks = generate_repponen_grid_data(w, h, num_cols, base_rows, chaos, brightness, seed_val)

        for frame_number in range(total_frames):
            t = frame_number / fps
            f_out = np.empty_like(img_arr)
            np.copyto(f_out, img_arr)

            if stijl == "Classic Glitch (Vloeiend)":
                for idx, b in enumerate(bands):
                    angle = (2 * math.pi * (b["cycles"] * t / max(duration, 1)) + b["phase"])
                    movement = math.sin(angle)
                    shift = int(movement * (w * 0.5) * b["direction"] * anim_speed)
                    shifted = np.roll(pre_rows[idx], shift, axis=1)
                    f_out[b["y1"]:b["y2"], :, :] = shifted
                    del shifted
            else:
                for b in blocks:
                    x1, x2, y1, y2 = b["x1"], b["x2"], b["y1"], b["y2"]
                    bw = x2 - x1
                    if bw <= 0: continue

                    offset = int(math.sin(t * anim_speed * b["speed"] + b["phase"]) * (bw / 2.5))
                    sx = int(np.clip(b["sample_x"] + offset, x1, x2 - 1))
                    src = img_arr[y1:y2, sx:sx + 1, :]
                    block = np.broadcast_to(src, (y2 - y1, bw, 3))

                    if b["brightness"] != 1.0:
                        block = np.clip(block.astype(np.float32) * b["brightness"], 0, 255).astype(np.uint8)
                    f_out[y1:y2, x1:x2, :] = block
                    del block

            try:
                proc.stdin.write(f_out.tobytes())
            except BrokenPipeError:
                stderr_data = b""
                try: stderr_data = proc.stderr.read()
                except Exception: pass
                message = stderr_data.decode("utf-8", errors="replace") if stderr_data else "FFmpeg stopte onverwacht."
                raise RuntimeError(message)
            finally:
                del f_out

            if frame_number % max(1, fps // 2) == 0 or frame_number == total_frames - 1:
                progress_bar.progress(min(1.0, (frame_number + 1) / total_frames))

        try:
            proc.stdin.close()
        except Exception:
            pass

        return_code = proc.wait()
        stderr_data = b""
        try:
            stderr_data = proc.stderr.read()
        except Exception:
            pass

        if return_code != 0:
            error_text = stderr_data.decode("utf-8", errors="replace")
            raise RuntimeError(error_text or "FFmpeg kon de video niet renderen.")

        if not output_path or not os.path.exists(output_path):
            raise RuntimeError("FFmpeg heeft geen MP4-bestand geproduceerd.")

        file_size = os.path.getsize(output_path)
        if file_size < 1000:
            raise RuntimeError("Het gegenereerde MP4-bestand is ongeldig of leeg.")

        progress_bar.progress(1.0)
        return output_path

    except Exception:
        if proc is not None:
            try:
                if proc.poll() is None:
                    proc.kill()
            except Exception: pass
            try:
                if proc.stdin:
                    proc.stdin.close()
            except Exception: pass
        cleanup_file(output_path)
        raise
    finally:
        gc.collect()

def make_png_bytes(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()

# ============================================================
# 8. SIDEBAR
# ============================================================

with st.sidebar:
    st.title("🎛️ Project Setup")
    uploaded = st.file_uploader(
        "1. Media", type=["jpg", "jpeg", "png", "webp"], help=f"Maximum {MAX_UPLOAD_MB} MB."
    )
    stijl = st.selectbox(
        "2. Engine", ["Classic Glitch (Vloeiend)", "Repponen Grid (Blokken)"]
    )
    modus = st.radio(
        "3. Output Type", ["🖼️ Statisch Beeld", "🎥 Motion (MP4)"]
    )

# ============================================================
# 9. START
# ============================================================

if not uploaded:
    st.info("👋 Sleep een afbeelding in het uploadveld om te beginnen.")
    if modus == "🎥 Motion (MP4)":
        if check_ffmpeg():
            st.caption(f"✅ {get_ffmpeg_version()}")
        else:
            st.warning("⚠️ FFmpeg is niet gevonden. Motion/MP4 werkt dan niet.")
    st.stop()

img = image_from_uploaded_file(uploaded)
if img is None:
    st.stop()

col_controls, col_canvas = st.columns([1.2, 2], gap="large")

with col_controls:
    tab_design, tab_motion, tab_render = st.tabs(["🎨 Vormgeving", "🎞️ Motion", "⚙️ Export"])

    with tab_design:
        st.subheader("Look & Feel")
        if stijl == "Classic Glitch (Vloeiend)":
            bands_count = st.slider("Glitch Dichtheid", 10, 300, 100)
            complexity = st.slider("Segment Complexiteit", 1, 10, 4)
            num_cols, base_rows, chaos, brightness = 40, 100, 0.35, 0.15
        else:
            num_cols = st.slider("Verticale Kolommen", 2, 150, 40)
            base_rows = st.slider("Horizontale Rijen", 10, 300, 100)
            chaos = st.slider("Asymmetrie (Chaos)", 0.0, 0.8, 0.35, step=0.05)
            brightness = st.slider("Blok Contrast", 0.0, 0.5, 0.15, step=0.05)
            bands_count, complexity = 100, 4

        seed_val = st.number_input("Variatie Seed", value=42, step=1)

    with tab_motion:
        if modus == "🎥 Motion (MP4)":
            st.subheader("Animatie Dynamiek")
            anim_speed = st.slider("Globale Snelheid", 0.05, 5.0, 1.0, step=0.05)
            duration = st.select_slider("Duur (seconden)", options=[5, 10, 15, 20, 30], value=10)
            fps = st.select_slider("Framerate", options=[24, 30], value=30)
            st.caption(f"Beveiligd maximum: {MAX_VIDEO_DURATION}s / {MAX_VIDEO_FPS} FPS / 1920×1080.")
        else:
            anim_speed, duration, fps = 1.0, 10, 30
            st.info("Schakel naar Motion (MP4) voor animatie-instellingen.")

    with tab_render:
        st.subheader("Output Kwaliteit")
        resolution_options = ["1920x1080 (Full HD)", "1280x720 (HD)", "Origineel"]
        resolutie = st.selectbox("Resolutie", resolution_options, index=0)

        if modus == "🎥 Motion (MP4)":
            quality = st.selectbox("Videokwaliteit", ["🔥 Zeer hoge kwaliteit", "⚡ Sneller renderen", "💎 Maximale kwaliteit"], index=0)
            if quality == "💎 Maximale kwaliteit":
                crf, preset = 16, "medium"
            elif quality == "🔥 Zeer hoge kwaliteit":
                crf, preset = 18, "fast"
            else:
                crf, preset = 21, "veryfast"
            st.caption(f"H.264 • CRF {crf} • preset {preset}")
        else:
            crf, preset = 18, "fast"

        render_btn = st.button("🚀 Start Render", type="primary")

with col_canvas:
    with st.expander("📸 Bekijk bronbestand", expanded=False):
        st.image(img, use_container_width=True)

    if render_btn:
        if modus == "🎥 Motion (MP4)" and not check_ffmpeg():
            st.error("❌ FFmpeg is niet beschikbaar.")
            st.info("Voeg `ffmpeg` toe aan packages.txt als je Streamlit Cloud gebruikt.")
            st.stop()

        with st.spinner("Afbeelding voorbereiden..."):
            target_img = prepare_output_image(img, resolutie, for_video=(modus == "🎥 Motion (MP4)"))

        if target_img is None:
            st.stop()

        img_arr = None
        output_path = None

        try:
            img_arr = np.asarray(target_img, dtype=np.uint8).copy()
            h, w, _ = img_arr.shape
            st.write(f"**Output:** {w} × {h} px")

            if modus == "🖼️ Statisch Beeld":
                with st.spinner("Glitch afbeelding maken..."):
                    if stijl == "Classic Glitch (Vloeiend)":
                        bands = generate_classic_glitch_data(w, h, bands_count, complexity, seed_val)
                        out_arr = render_static_classic(img_arr, bands)
                    else:
                        blocks = generate_repponen_grid_data(w, h, num_cols, base_rows, chaos, brightness, seed_val)
                        out_arr = render_static_grid(img_arr, blocks)

                    res_img = Image.fromarray(out_arr)

                st.success("✅ Glitch afbeelding klaar!")
                st.image(res_img, use_container_width=True)

                with st.spinner("PNG voorbereiden..."):
                    png_bytes = make_png_bytes(res_img)

                st.download_button("⬇️ Download PNG", data=png_bytes, file_name="glitch_export.png", mime="image/png")
                del out_arr, res_img, png_bytes

            else:
                total_frames = int(duration * fps)
                st.write(f"**Video:** {duration} sec • {fps} FPS • {total_frames} frames")
                progress = st.progress(0)

                try:
                    output_path = render_video(
                        img_arr=img_arr,
                        stijl=stijl,
                        bands_count=bands_count if stijl == "Classic Glitch (Vloeiend)" else 100,
                        complexity=complexity if stijl == "Classic Glitch (Vloeiend)" else 4,
                        num_cols=num_cols if stijl != "Classic Glitch (Vloeiend)" else 40,
                        base_rows=base_rows if stijl != "Classic Glitch (Vloeiend)" else 100,
                        chaos=chaos if stijl != "Classic Glitch (Vloeiend)" else 0.35,
                        brightness=brightness if stijl != "Classic Glitch (Vloeiend)" else 0.15,
                        seed_val=seed_val,
                        duration=duration,
                        fps=fps,
                        anim_speed=anim_speed,
                        crf=crf,
                        preset=preset,
                        progress_bar=progress,
                    )

                    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    st.success(f"✅ Render voltooid! MP4: {file_size_mb:.1f} MB")
                    st.video(output_path)

                    with open(output_path, "rb") as video_file:
                        video_bytes = video_file.read()

                    st.download_button("⬇️ Download MP4", data=video_bytes, file_name="smooth_glitch.mp4", mime="video/mp4")
                    del video_bytes

                except MemoryError:
                    st.error("❌ Onvoldoende geheugen tijdens het renderen.")
                    st.info("Gebruik 1280×720, 24/30 FPS en maximaal 10–15 seconden.")
                except BrokenPipeError:
                    st.error("❌ FFmpeg is onverwacht gestopt.")
                    st.info("Probeer 1280×720 of een kortere video.")
                except Exception as e:
                    st.error("❌ De render is niet gelukt.")
                    st.caption(f"Technische fout: {type(e).__name__}")
                    with st.expander("🔧 Technische details"):
                        st.code(str(e))
                finally:
                    cleanup_file(output_path)
                    output_path = None

            del img_arr, target_img
            gc.collect()

        except MemoryError:
            st.error("❌ De afbeelding is te groot voor het beschikbare geheugen.")
            st.info("Gebruik 1920×1080 of 1280×720.")
        except Exception as e:
            st.error("❌ Er ging iets mis tijdens het renderen.")
            st.caption(f"Technische fout: {type(e).__name__}")
            with st.expander("🔧 Technische details"):
                st.code(str(e))
        finally:
            if img_arr is not None:
                try: del img_arr
                except Exception: pass
            if target_img is not None:
                try: del target_img
                except Exception: pass
            cleanup_file(output_path)
            gc.collect()
