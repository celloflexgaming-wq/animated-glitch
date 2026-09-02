import streamlit as st
import numpy as np
from PIL import Image
import subprocess
import tempfile
import os
import math
import io

st.set_page_config(
    page_title="Architectural Stretch Studio",
    layout="centered"
)

# --- MOBIELE UI OPTIMALISATIE (CSS) ---
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
        padding-left: 1rem;
        padding-right: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏛️ Architectural Stretch Studio")
st.markdown("*Geïnspireerd door Anton Repponen's gestructureerde time-stretch esthetiek.*")

uploaded = st.file_uploader(
    "Upload een foto",
    type=["jpg", "jpeg", "png", "webp"]
)

# --- KERN ALGORITME VOOR DE STIJL ---
def generate_architectural_blocks(width, height, num_cols, split_complexity, seed=42):
    """
    Verdeelt het canvas in strakke rechthoekige blokken op basis van willekeur.
    Elk blok onthoudt zijn coördinaten en waaruit het de kleur moet 'samplen'.
    """
    rng = np.random.default_rng(seed)
    
    # 1. Bepaal de verticale scheidingslijnen (Kolommen)
    col_edges = [0]
    curr_x = 0
    while curr_x < width:
        # Varieer de breedte van de kolommen licht
        step = max(2, int(rng.normal(width / num_cols, (width / num_cols) * 0.6)))
        curr_x += step
        if curr_x >= width - (width / num_cols * 0.2): 
            break
        col_edges.append(curr_x)
    col_edges.append(width)
    
    blocks = []
    # 2. Loop door elke kolom en fragmenteer deze horizontaal
    for i in range(len(col_edges)-1):
        x1, x2 = col_edges[i], col_edges[i+1]
        
        y_edges = [0]
        curr_y = 0
        while curr_y < height:
            # Kans dat een kolom horizontaal wordt doorgeknipt
            if rng.random() < split_complexity:
                step = rng.integers(height // 20, height // 2)
                curr_y += step
                if curr_y >= height - (height // 20):
                    break
                y_edges.append(curr_y)
            else:
                break
        y_edges.append(height)
        
        # 3. Genereer de uiteindelijke blok data
        for j in range(len(y_edges)-1):
            y1, y2 = y_edges[j], y_edges[j+1]
            
            # Kies een start x-coördinaat om te samplen (dit bepaalt de kleur van het blok)
            sample_x = rng.integers(max(0, x1 - width//10), min(width, x2 + width//10))
            
            blocks.append({
                'x1': x1, 'x2': x2, 
                'y1': y1, 'y2': y2,
                'base_sample_x': sample_x,
                'phase': rng.random() * 2 * math.pi,  # Voor soepele video-animatie
                'speed_mult': rng.uniform(0.3, 1.8)   # Ieder blok beweegt in video op eigen tempo
            })
            
    return blocks


if uploaded:
    img = Image.open(uploaded).convert("RGB")

    st.image(
        img,
        caption="Originele foto",
        use_container_width=True
    )

    st.markdown("---")
    mode = st.radio(
        "Kies wat je wilt genereren:",
        ["🖼️ Architecturale Foto (Statisch)", "🎥 Architecturale Video (MP4)"],
        horizontal=True
    )
    st.markdown("---")

    # =========================================
    # MODUS 1: STATISCHE FOTO
    # =========================================
    if mode == "🖼️ Architecturale Foto (Statisch)":
        st.subheader("⚙️ Vormgeving & Stijl")

        resolution_photo = st.selectbox(
            "Foto resolutie",
            ["1920 × 1080 — Full HD", "1280 × 720 — HD", "Originele beeldverhouding behouden"],
            index=0
        )

        col1, col2 = st.columns(2)
        with col1:
            num_cols_photo = st.slider(
                "Aantal Kolommen", 
                min_value=5, max_value=120, value=40,
                help="Bepaalt hoe dun/breed de verticale elementen zijn."
            )
        with col2:
            complexity_photo = st.slider(
                "Horizontale Fragmentatie", 
                min_value=0.0, max_value=1.0, value=0.4, step=0.05,
                help="Hoe vaak de kolommen worden onderbroken door 'zwevende' blokken."
            )
            
        seed_photo = st.number_input("Willekeur Seed (Verander voor een andere layout)", value=42)

        if st.button("🖼️ Genereer Kunstwerk", type="primary"):
            # Resolutie en crop logica
            if "1920" in resolution_photo:
                target_w, target_h = 1920, 1080
            elif "1280" in resolution_photo:
                target_w, target_h = 1280, 720
            else:
                target_w, target_h = img.width, img.height

            source_ratio = img.width / img.height
            target_ratio = target_w / target_h

            if resolution_photo != "Originele beeldverhouding behouden":
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
            
            # Bouw de strakke blokken
            blocks = generate_architectural_blocks(width, height, num_cols_photo, complexity_photo, seed=seed_photo)
            
            # Pas de stretch toe
            output_array = np.zeros_like(img_array)
            for b in blocks:
                sx = np.clip(b['base_sample_x'], 0, width - 1)
                # Pak een verticale 1-pixel brede strip en rek deze uit over de breedte van het blok
                source_col = img_array[b['y1']:b['y2'], sx:sx+1, :]
                output_array[b['y1']:b['y2'], b['x1']:b['x2'], :] = np.repeat(source_col, b['x2'] - b['x1'], axis=1)

            result_img = Image.fromarray(output_array)
            st.image(result_img, caption="Gegenereerd Architecturaal Meesterwerk", use_container_width=True)

            buf = io.BytesIO()
            result_img.save(buf, format="PNG")
            st.download_button(
                label="⬇️ Download Kunstwerk (PNG)",
                data=buf.getvalue(),
                file_name="architectural_stretch.png",
                mime="image/png"
            )

    # =========================================
    # MODUS 2: VIDEO (MP4)
    # =========================================
    elif mode == "🎥 Architecturale Video (MP4)":
        st.subheader("⚙️ Video & Animatie Instellingen")

        resolution = st.selectbox("Videoresolutie", ["1920 × 1080 — Full HD", "1280 × 720 — HD"], index=0)
        
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            duration = st.selectbox("Duur (seconden)", [5, 10, 15, 20, 30], index=1)
            num_cols_video = st.slider("Aantal Kolommen", 5, 120, 40)
            anim_speed = st.slider("Animatie Snelheid", 0.5, 5.0, 1.5, step=0.1)
            
        with col_v2:
            fps = st.selectbox("FPS", [24, 30, 60], index=1)
            complexity_video = st.slider("Horizontale Fragmentatie", 0.0, 1.0, 0.4, step=0.05)
            pan_amount = st.slider("Scan Bereik", 0.01, 0.5, 0.1, step=0.01, help="Hoe ver de stretch door de originele foto scant.")

        quality = st.selectbox("Videokwaliteit", ["Maximale kwaliteit (CRF 12)", "Zeer hoge kwaliteit (CRF 16)", "Hoge kwaliteit (CRF 20)"], index=0)
        seed_video = st.number_input("Layout Seed", value=42, key="seed_vid")

        if quality.startswith("Max"):
            crf, preset = 12, "slow"
        elif quality.startswith("Zeer"):
            crf, preset = 16, "medium"
        else:
            crf, preset = 20, "medium"

        if st.button("🎬 Maak Animatie (Renderen)", type="primary"):
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
            height, width, channels = img_array.shape
            total_frames = int(duration * fps)

            st.write(f"**Bezig met voorbereiden...** ({width}×{height}, {total_frames} frames)")
            
            # Genereer de blok-layout
            blocks = generate_architectural_blocks(width, height, num_cols_video, complexity_video, seed=seed_video)

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

            try:
                for frame_number in range(total_frames):
                    t = frame_number / fps
                    frame_out = np.zeros_like(img_array)

                    for b in blocks:
                        # Bereken de beweging (scan effect) voor dit specifieke blok d.m.v. een sinusgolf
                        offset = int(math.sin(t * anim_speed * b['speed_mult'] + b['phase']) * (width * pan_amount))
                        sx = np.clip(b['base_sample_x'] + offset, 0, width - 1)
                        
                        # Pas de stretch toe
                        source_col = img_array[b['y1']:b['y2'], sx:sx+1, :]
                        frame_out[b['y1']:b['y2'], b['x1']:b['x2'], :] = np.repeat(source_col, b['x2'] - b['x1'], axis=1)

                    process.stdin.write(frame_out.tobytes())

                    if frame_number % max(1, fps // 4) == 0:
                        progress.progress(min(1.0, (frame_number + 1) / total_frames))

                process.stdin.close()
                stderr = process.stderr.read()
                return_code = process.wait()

                if return_code != 0:
                    st.error("FFmpeg fout:\n\n" + stderr.decode("utf-8", errors="replace"))
                    raise RuntimeError("Kon video niet maken.")

            except Exception:
                try: process.stdin.close()
                except: pass
                process.kill()
                raise

            progress.progress(1.0)
            with open(output_path, "rb") as f:
                video_bytes = f.read()

            st.success("✅ Video renderen is voltooid!")
            st.video(video_bytes)
            st.download_button(
                label="⬇️ Download Geanimeerd Meesterwerk (MP4)",
                data=video_bytes,
                file_name="architectural_stretch_anim.mp4",
                mime="video/mp4"
            )

            try: os.remove(output_path)
            except: pass
