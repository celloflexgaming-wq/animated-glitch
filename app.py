import streamlit as st
import numpy as np
from PIL import Image
import subprocess
import tempfile
import os
import math
import io
import gc

st.set_page_config(
    page_title="Time Stretch Studio PRO",
    layout="centered"
)

# --- UI OPTIMALISATIE ---
st.markdown("""
    <style>
    .stButton > button, .stDownloadButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        height: 3em;
    }
    .stFileUploader {
        padding: 10px;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏙️ Time Stretch Studio PRO")
st.markdown("*Geavanceerde architecturale maskers en slit-scan generatie.*")

uploaded = st.file_uploader(
    "Upload een foto",
    type=["jpg", "jpeg", "png", "webp"]
)

# --- KERN ALGORITME (REPPONEN STIJL) ---
def generate_masked_slitscan_blocks(width, height, num_bands, split_complexity, keep_original_prob, seed=42):
    """
    Verdeelt het beeld in asymmetrische blokken. Sommige blokken behouden de originele
    fotografie (masking), andere blokken krijgen de extreme horizontale slit-scan stretch.
    """
    rng = np.random.default_rng(seed)
    blocks = []
    
    # 1. Bepaal horizontale scheidingslijnen (Verdiepingen/Banden)
    y_edges = [0]
    curr_y = 0
    while curr_y < height:
        # Wisselende diktes voor de banden
        step = max(4, int(rng.normal(height / num_bands, (height / num_bands) * 0.7)))
        curr_y += step
        if curr_y >= height - (height // 20): 
            break
        y_edges.append(curr_y)
    y_edges.append(height)
    
    # 2. Fragmenteer elke band verticaal en wijs eigenschappen toe
    for i in range(len(y_edges)-1):
        y1, y2 = y_edges[i], y_edges[i+1]
        
        x_edges = [0]
        curr_x = 0
        while curr_x < width:
            if rng.random() < split_complexity:
                step = rng.integers(width // 15, width // 2)
                curr_x += step
                if curr_x >= width - (width // 20):
                    break
                x_edges.append(curr_x)
            else:
                break
        x_edges.append(width)
        
        for j in range(len(x_edges)-1):
            x1, x2 = x_edges[j], x_edges[j+1]
            
            # Beslis of dit blok origineel fotomateriaal toont of gestretcht wordt
            is_original = rng.random() < keep_original_prob
            
            # Als we stretchen, waar halen we de 1-pixel sample vandaan?
            sample_x = rng.integers(0, width)
            
            blocks.append({
                'x1': x1, 'x2': x2, 
                'y1': y1, 'y2': y2,
                'is_original': is_original,
                'base_sample_x': sample_x,
                'phase': rng.random() * 2 * math.pi,
                'speed_mult': rng.uniform(0.2, 1.5) * rng.choice([-1, 1])
            })
            
    return blocks

if uploaded:
    img = Image.open(uploaded).convert("RGB")

    st.image(img, caption="Originele foto", use_container_width=True)
    st.markdown("---")
    
    mode = st.radio(
        "Kies wat je wilt genereren:",
        ["🖼️ High-Res Foto Export", "🎥 Animatie Render (MP4)"],
        horizontal=True
    )
    st.markdown("---")

    # =========================================
    # MODUS 1: STATISCHE FOTO
    # =========================================
    if mode == "🖼️ High-Res Foto Export":
        st.subheader("⚙️ Compositie Instellingen")

        resolution_photo = st.selectbox("Resolutie", ["1920 × 1080 (16:9)", "1280 × 720 (16:9)", "Originele beeldverhouding"], index=0)

        col1, col2 = st.columns(2)
        with col1:
            num_bands = st.slider("Aantal Horizontale Banden", 10, 200, 60, help="Vergelijkbaar met het aantal scanlines of verdiepingen.")
            complexity = st.slider("Verticale Fragmentatie", 0.0, 1.0, 0.6, step=0.05)
        with col2:
            keep_prob = st.slider("Detail Behoud (Masking)", 0.0, 1.0, 0.15, step=0.05, help="Hoeveel originele foto elementen er door de stretch heen prikken.")
            seed_photo = st.number_input("Willekeur Seed (Verander de layout)", value=123)

        if st.button("🖼️ Genereer Master", type="primary"):
            # Resolutie setup
            if "1920" in resolution_photo:
                target_w, target_h = 1920, 1080
            elif "1280" in resolution_photo:
                target_w, target_h = 1280, 720
            else:
                target_w, target_h = img.width, img.height

            if resolution_photo != "Originele beeldverhouding":
                source_ratio = img.width / img.height
                target_ratio = target_w / target_h
                if source_ratio > target_ratio:
                    new_width = int(img.height * target_ratio)
                    left = (img.width - new_width) // 2
                    img = img.crop((left, 0, left + new_width, img.height))
                elif source_ratio < target_ratio:
                    new_height = int(img.width / target_ratio)
                    top = (img.height - new_height) // 2
                    img = img.crop((0, top, img.width, top + new_height))
                img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

            img_array = np.array(img, dtype=np.uint8)
            height, width, _ = img_array.shape
            
            blocks = generate_masked_slitscan_blocks(width, height, num_bands, complexity, keep_prob, seed=seed_photo)
            
            # Geheugenefficiënte output array
            output_array = np.empty_like(img_array)
            
            for b in blocks:
                if b['is_original']:
                    # Masker: Teken direct de originele foto
                    output_array[b['y1']:b['y2'], b['x1']:b['x2'], :] = img_array[b['y1']:b['y2'], b['x1']:b['x2'], :]
                else:
                    # Slit-scan: Rek een 1-pixel strip volledig uit
                    sx = np.clip(b['base_sample_x'], 0, width - 1)
                    source_col = img_array[b['y1']:b['y2'], sx:sx+1, :]
                    output_array[b['y1']:b['y2'], b['x1']:b['x2'], :] = np.repeat(source_col, b['x2'] - b['x1'], axis=1)

            result_img = Image.fromarray(output_array)
            st.image(result_img, caption="Time Stretched Resultaat", use_container_width=True)

            buf = io.BytesIO()
            result_img.save(buf, format="PNG", optimize=True)
            st.download_button(
                label="⬇️ Download PNG",
                data=buf.getvalue(),
                file_name="time_stretch_master.png",
                mime="image/png"
            )

    # =========================================
    # MODUS 2: VIDEO (MP4)
    # =========================================
    elif mode == "🎥 Animatie Render (MP4)":
        st.subheader("⚙️ Render & Animatie Instellingen")

        resolution = st.selectbox("Render Resolutie", ["1920 × 1080 (Full HD)", "1280 × 720 (HD)"], index=1)
        
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            duration = st.selectbox("Duur", [5, 10, 15, 20], index=1, format_func=lambda x: f"{x} seconden")
            num_bands_v = st.slider("Aantal Banden", 10, 150, 60)
            anim_speed = st.slider("Pan Snelheid", 0.1, 3.0, 0.8, step=0.1)
            
        with col_v2:
            fps = st.selectbox("Framerate", [24, 30, 60], index=0)
            complexity_v = st.slider("Verticale Fragmentatie", 0.0, 1.0, 0.6, step=0.05)
            keep_prob_v = st.slider("Detail Behoud", 0.0, 1.0, 0.15, step=0.05)

        quality = st.selectbox("Output Kwaliteit", ["Hoge Kwaliteit (CRF 18)", "Web Geoptimaliseerd (CRF 23)"], index=0)
        seed_video = st.number_input("Layout Seed", value=42, key="seed_vid")

        crf, preset = (18, "medium") if quality.startswith("Hoge") else (23, "fast")

        if st.button("🎬 Start Render Queue", type="primary"):
            target_width = 1920 if resolution.startswith("1920") else 1280
            target_height = 1080 if resolution.startswith("1920") else 720

            source_ratio = img.width / img.height
            target_ratio = target_width / target_height

            if source_ratio > target_ratio:
                new_width = int(img.height * target_ratio)
                left = (img.width - new_width) // 2
                img = img.crop((left, 0, left + new_width, img.height))
            elif source_ratio < target_ratio:
                new_height = int(img.width / target_ratio)
                top = (img.height - new_height) // 2
                img = img.crop((0, top, img.width, top + new_height))

            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            img_array = np.array(img, dtype=np.uint8)
            height, width, _ = img_array.shape
            total_frames = int(duration * fps)
            
            blocks = generate_masked_slitscan_blocks(width, height, num_bands_v, complexity_v, keep_prob_v, seed=seed_video)

            progress = st.progress(0)
            output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            output_path = output_file.name
            output_file.close()

            command = [
                "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
                "-vcodec", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}",
                "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264",
                "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", output_path
            ]

            process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

            # RAM Optimalisatie: Slechts 1 actieve render-buffer die wordt gerecycled
            frame_out = np.empty_like(img_array)

            try:
                for frame_number in range(total_frames):
                    t = frame_number / fps

                    for b in blocks:
                        if b['is_original']:
                            frame_out[b['y1']:b['y2'], b['x1']:b['x2'], :] = img_array[b['y1']:b['y2'], b['x1']:b['x2'], :]
                        else:
                            # Animatie: De sample-lijn beweegt subtiel horizontaal door de tijd
                            offset = int(math.sin(t * anim_speed * b['speed_mult'] + b['phase']) * (width * 0.15))
                            sx = np.clip(b['base_sample_x'] + offset, 0, width - 1)
                            
                            source_col = img_array[b['y1']:b['y2'], sx:sx+1, :]
                            frame_out[b['y1']:b['y2'], b['x1']:b['x2'], :] = np.repeat(source_col, b['x2'] - b['x1'], axis=1)

                    process.stdin.write(frame_out.tobytes())

                    # Progress update & RAM clean-up
                    if frame_number % max(1, fps // 4) == 0:
                        progress.progress(min(1.0, (frame_number + 1) / total_frames))
                        gc.collect()

                process.stdin.close()
                if process.wait() != 0:
                    st.error("FFmpeg fout bij het encoderen.")
                    raise RuntimeError("Render gefaald.")

            except Exception:
                try: process.stdin.close()
                except: pass
                process.kill()
                raise

            progress.progress(1.0)
            with open(output_path, "rb") as f:
                video_bytes = f.read()

            st.success("✅ Render Voltooid!")
            st.video(video_bytes)
            st.download_button(
                label="⬇️ Download MP4",
                data=video_bytes,
                file_name="time_stretch_anim.mp4",
                mime="video/mp4"
            )
            try: os.remove(output_path)
            except: pass
