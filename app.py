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
    page_title="Anton Repponen Style Studio",
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

st.title("🏙️ Architectural Time Stretch")
st.markdown("*Nauwkeurige recreatie van de Anton Repponen esthetiek middels strakke maskers.*")

uploaded = st.file_uploader(
    "Upload een foto",
    type=["jpg", "jpeg", "png", "webp"]
)

def generate_repponen_masterpiece(img_array, num_bands, num_masks, min_size_pct, max_size_pct, seed=42):
    """
    Creëert de perfecte Repponen stijl:
    1. Een basislaag van perfecte horizontale stretches.
    2. Een toplaag van strakke rechthoekige maskers die het origineel onthullen.
    """
    rng = np.random.default_rng(seed)
    height, width, _ = img_array.shape
    output = np.empty_like(img_array)
    
    # LAAG 1: De Horizontale Stretch
    y_edges = [0]
    curr_y = 0
    while curr_y < height:
        step = max(2, int(rng.normal(height / num_bands, (height / num_bands) * 0.5)))
        curr_y += step
        if curr_y >= height - (height // 20): 
            break
        y_edges.append(curr_y)
    y_edges.append(height)
    
    # Bewaar de sample coördinaten voor video-animatie
    band_data = []
    for i in range(len(y_edges)-1):
        y1, y2 = y_edges[i], y_edges[i+1]
        sample_x = rng.integers(0, width)
        band_data.append({
            'y1': y1, 'y2': y2,
            'base_x': sample_x,
            'phase': rng.random() * 2 * math.pi,
            'speed': rng.uniform(0.1, 1.0) * rng.choice([-1, 1])
        })
        # Vul de statische array direct
        output[y1:y2, :, :] = np.repeat(img_array[y1:y2, sample_x:sample_x+1, :], width, axis=1)

    # LAAG 2: De Originele Maskers (Track Mattes)
    mask_data = []
    min_w, max_w = int(width * min_size_pct), int(width * max_size_pct)
    min_h, max_h = int(height * min_size_pct), int(height * max_size_pct)
    
    for _ in range(num_masks):
        w = rng.integers(max(1, min_w), max(2, max_w))
        h = rng.integers(max(1, min_h), max(2, max_h))
        x1 = rng.integers(0, max(1, width - w))
        y1 = rng.integers(0, max(1, height - h))
        
        mask_data.append({'x1': x1, 'x2': x1+w, 'y1': y1, 'y2': y1+h})
        output[y1:y1+h, x1:x1+w, :] = img_array[y1:y1+h, x1:x1+w, :]
        
    return output, band_data, mask_data

if uploaded:
    img = Image.open(uploaded).convert("RGB")
    st.image(img, caption="Originele foto", use_container_width=True)
    st.markdown("---")
    
    mode = st.radio("Output Formaat:", ["🖼️ Statisch Kunstwerk", "🎥 Geanimeerde Loop (MP4)"], horizontal=True)
    st.markdown("---")

    if mode == "🖼️ Statisch Kunstwerk":
        st.subheader("⚙️ Compositie Instellingen")
        
        col1, col2 = st.columns(2)
        with col1:
            num_bands = st.slider("Aantal Stretch Stroken", 20, 200, 80, help="Dikte van de abstracte achtergrondlijnen.")
            num_masks = st.slider("Aantal Fotomaskers", 1, 50, 15, help="Hoeveel originele rechthoeken er zichtbaar blijven.")
        with col2:
            min_size = st.slider("Minimale Masker Grootte (%)", 1, 20, 5) / 100
            max_size = st.slider("Maximale Masker Grootte (%)", 10, 80, 40) / 100
            seed_photo = st.number_input("Variatie Seed", value=101)

        if st.button("🖼️ Genereer Master", type="primary"):
            img_array = np.array(img, dtype=np.uint8)
            output_array, _, _ = generate_repponen_masterpiece(
                img_array, num_bands, num_masks, min_size, max_size, seed_photo
            )

            result_img = Image.fromarray(output_array)
            st.image(result_img, caption="Perfecte Repponen Stijl", use_container_width=True)

            buf = io.BytesIO()
            result_img.save(buf, format="PNG")
            st.download_button(label="⬇️ Download High-Res PNG", data=buf.getvalue(), file_name="repponen_style.png", mime="image/png")

    elif mode == "🎥 Geanimeerde Loop (MP4)":
        st.subheader("⚙️ Animatie Instellingen")
        
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            duration = st.selectbox("Duur (seconden)", [5, 10, 15], index=1)
            num_bands = st.slider("Aantal Stretch Stroken", 20, 200, 80)
            num_masks = st.slider("Aantal Fotomaskers", 1, 50, 15)
        with col_v2:
            pan_speed = st.slider("Pan Snelheid", 0.05, 1.0, 0.2)
            min_size = st.slider("Minimale Masker Grootte (%)", 1, 20, 5) / 100
            max_size = st.slider("Maximale Masker Grootte (%)", 10, 80, 40) / 100
            seed_vid = st.number_input("Variatie Seed", value=101, key="vid_seed")

        if st.button("🎬 Render Video", type="primary"):
            # Optimaliseer resolutie voor cloud rendering
            target_w, target_h = 1280, 720
            source_ratio = img.width / img.height
            target_ratio = target_w / target_h
            
            if source_ratio > target_ratio:
                new_w = int(img.height * target_ratio)
                img = img.crop(((img.width - new_w)//2, 0, (img.width + new_w)//2, img.height))
            else:
                new_h = int(img.width / target_ratio)
                img = img.crop((0, (img.height - new_h)//2, img.width, (img.height + new_h)//2))
                
            img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            img_array = np.array(img, dtype=np.uint8)
            height, width, _ = img_array.shape
            
            fps = 30
            total_frames = duration * fps
            
            _, band_data, mask_data = generate_repponen_masterpiece(img_array, num_bands, num_masks, min_size, max_size, seed_vid)
            
            progress = st.progress(0)
            output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            output_path = output_file.name
            output_file.close()

            command = [
                "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
                "-vcodec", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}",
                "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264",
                "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p", output_path
            ]
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            frame_buffer = np.empty_like(img_array)

            try:
                for frame in range(total_frames):
                    t = frame / fps
                    
                    # Reken de geanimeerde stretch uit
                    for b in band_data:
                        offset = int(math.sin(t * pan_speed * b['speed'] + b['phase']) * (width * 0.2))
                        sx = np.clip(b['base_x'] + offset, 0, width - 1)
                        frame_buffer[b['y1']:b['y2'], :, :] = np.repeat(img_array[b['y1']:b['y2'], sx:sx+1, :], width, axis=1)
                        
                    # Plak de originele maskers er hard overheen
                    for m in mask_data:
                        frame_buffer[m['y1']:m['y2'], m['x1']:m['x2'], :] = img_array[m['y1']:m['y2'], m['x1']:m['x2'], :]
                        
                    process.stdin.write(frame_buffer.tobytes())
                    if frame % 15 == 0:
                        progress.progress(min(1.0, (frame + 1) / total_frames))
                        gc.collect()

                process.stdin.close()
                process.wait()
            except Exception:
                process.kill()
                raise

            progress.progress(1.0)
            with open(output_path, "rb") as f:
                st.video(f.read())
            st.success("✅ Render Voltooid!")
