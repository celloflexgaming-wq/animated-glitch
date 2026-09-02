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
    page_title="Repponen Extrusion Studio",
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

st.title("🏙️ The Repponen Extrusion Studio")
st.markdown("*Exacte recreatie van 'Time Stretched': Intacte architectuur waarvan de randen horizontaal in het oneindige worden uitgesmeerd.*")

uploaded = st.file_uploader(
    "Upload een foto",
    type=["jpg", "jpeg", "png", "webp"]
)

def generate_extrusion_masterpiece(img_array, num_bands, extrusion_chance, seed=42):
    """
    Het ware Repponen algoritme:
    1. Genereert onzichtbare 'verticale hulplijnen' (guides) voor architecturale structuur.
    2. Kiest per horizontale band of het een 'Extrusie' wordt of een 'Solid Stretch'.
    3. Extrusie: Een rechthoekig deel van de foto blijft 100% intact. De zijkanten worden vanaf de randpixels uitgesmeerd.
    """
    rng = np.random.default_rng(seed)
    height, width, _ = img_array.shape
    output = np.empty_like(img_array)
    
    # 1. Genereer architecturale 'guides' zodat de blokken mooi uitlijnen als in een gebouw
    num_guides = rng.integers(4, 15)
    guides = sorted([rng.integers(0, width) for _ in range(num_guides)])
    guides = [0] + guides + [width]

    # 2. Bepaal horizontale banden (Verdiepingen)
    y_edges = [0]
    curr_y = 0
    while curr_y < height:
        # Repponen gebruikt een mix van héle dunne lijnen en dikkere blokken
        if rng.random() < 0.25:
            step = rng.integers(1, 5) # Dun
        else:
            step = rng.integers(5, max(10, height // (num_bands // 3))) # Dik
            
        curr_y += step
        if curr_y >= height - 2: 
            break
        y_edges.append(curr_y)
    y_edges.append(height)
    
    band_data = [] # Opgeslagen data voor de MP4 animatie
    
    for i in range(len(y_edges)-1):
        y1, y2 = y_edges[i], y_edges[i+1]
        
        if rng.random() < extrusion_chance:
            # TYPE A: EXTRUSIE (Het object is intact, de randen bloeden uit)
            idx1 = rng.integers(0, len(guides)-2)
            idx2 = rng.integers(idx1+1, min(idx1+3, len(guides)))
            x_start = guides[idx1]
            x_end = guides[idx2]
            
            if x_end <= x_start: x_end = x_start + 10
            
            # Plaats de intacte foto
            output[y1:y2, x_start:x_end, :] = img_array[y1:y2, x_start:x_end, :]
            
            # Smeer de linkerkant uit (vanaf de linkerrand van het intacte object)
            if x_start > 0:
                output[y1:y2, 0:x_start, :] = np.repeat(img_array[y1:y2, x_start:x_start+1, :], x_start, axis=1)
                
            # Smeer de rechterkant uit (vanaf de rechterrand van het intacte object)
            if x_end < width:
                output[y1:y2, x_end:width, :] = np.repeat(img_array[y1:y2, x_end-1:x_end, :], width - x_end, axis=1)
                
            band_data.append({
                'type': 'extrusion', 'y1': y1, 'y2': y2,
                'x_start': x_start, 'x_end': x_end,
                'phase': rng.random() * 2 * math.pi,
                'speed': rng.uniform(0.05, 0.3) * rng.choice([-1, 1])
            })
            
        else:
            # TYPE B: SOLID STRETCH (Volledig uitgesmeerde band)
            sample_x = rng.integers(0, width)
            output[y1:y2, :, :] = np.repeat(img_array[y1:y2, sample_x:sample_x+1, :], width, axis=1)
            
            band_data.append({
                'type': 'solid', 'y1': y1, 'y2': y2,
                'sample_x': sample_x,
                'phase': rng.random() * 2 * math.pi,
                'speed': rng.uniform(0.1, 0.8) * rng.choice([-1, 1])
            })

    return output, band_data

if uploaded:
    img = Image.open(uploaded).convert("RGB")
    st.image(img, caption="Originele foto", use_container_width=True)
    st.markdown("---")
    
    mode = st.radio("Output Formaat:", ["🖼️ Statisch Kunstwerk", "🎥 Geanimeerde Loop (MP4)"], horizontal=True)
    st.markdown("---")

    # =========================================
    # MODUS 1: STATISCHE FOTO
    # =========================================
    if mode == "🖼️ Statisch Kunstwerk":
        st.subheader("⚙️ Extrusie Instellingen")
        
        col1, col2 = st.columns(2)
        with col1:
            num_bands = st.slider("Aantal Horizontale Banden", 20, 200, 80, help="De mix tussen hele dunne en dikke lijnen.")
        with col2:
            extrusion_chance = st.slider("Object Behoud Ratio (%)", 0, 100, 45, help="Hoeveel procent van de banden een intact object toont met rand-extrusie.") / 100.0
            
        seed_photo = st.number_input("Architecturale Variatie (Seed)", value=88)

        if st.button("🖼️ Genereer Masterpiece", type="primary"):
            img_array = np.array(img, dtype=np.uint8)
            output_array, _ = generate_extrusion_masterpiece(img_array, num_bands, extrusion_chance, seed_photo)

            result_img = Image.fromarray(output_array)
            st.image(result_img, caption="Anton Repponen Style", use_container_width=True)

            buf = io.BytesIO()
            result_img.save(buf, format="PNG", optimize=True)
            st.download_button(label="⬇️ Download High-Res PNG", data=buf.getvalue(), file_name="repponen_extrusion.png", mime="image/png")

    # =========================================
    # MODUS 2: VIDEO (MP4)
    # =========================================
    elif mode == "🎥 Geanimeerde Loop (MP4)":
        st.subheader("⚙️ Animatie Instellingen")
        
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            duration = st.selectbox("Duur (seconden)", [5, 10, 15], index=1)
            num_bands = st.slider("Aantal Horizontale Banden", 20, 200, 80)
        with col_v2:
            extrusion_chance = st.slider("Object Behoud Ratio (%)", 0, 100, 45) / 100.0
            pan_speed = st.slider("X-Ray Scan Snelheid", 0.05, 1.0, 0.2, help="Snelheid waarmee de intacte objecten over de foto schuiven.")
            
        seed_vid = st.number_input("Architecturale Variatie (Seed)", value=88, key="vid_seed")

        if st.button("🎬 Render Extrusie Animatie", type="primary"):
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
            
            _, band_data = generate_extrusion_masterpiece(img_array, num_bands, extrusion_chance, seed_vid)
            
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
                    
                    for b in band_data:
                        if b['type'] == 'extrusion':
                            # Beweeg de 'lens' over het object
                            offset = int(math.sin(t * pan_speed * b['speed'] + b['phase']) * (width * 0.15))
                            n_start = np.clip(b['x_start'] + offset, 1, width - 2)
                            n_end = np.clip(b['x_end'] + offset, n_start + 1, width - 1)
                            
                            y1, y2 = b['y1'], b['y2']
                            frame_buffer[y1:y2, n_start:n_end, :] = img_array[y1:y2, n_start:n_end, :]
                            frame_buffer[y1:y2, 0:n_start, :] = np.repeat(img_array[y1:y2, n_start:n_start+1, :], n_start, axis=1)
                            frame_buffer[y1:y2, n_end:width, :] = np.repeat(img_array[y1:y2, n_end-1:n_end, :], width - n_end, axis=1)
                            
                        else:
                            # Solid stretch animatie
                            offset = int(math.sin(t * pan_speed * b['speed'] + b['phase']) * (width * 0.2))
                            sx = np.clip(b['sample_x'] + offset, 0, width - 1)
                            frame_buffer[b['y1']:b['y2'], :, :] = np.repeat(img_array[b['y1']:b['y2'], sx:sx+1, :], width, axis=1)
                        
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
