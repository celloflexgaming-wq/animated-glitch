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
    page_title="100% Time Stretch Studio",
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

st.title("🏙️ Pure Time Stretch Studio")
st.markdown("*100% abstracte stretch-dekking over het hele canvas, verdeeld in strakke asymmetrische blokken.*")

uploaded = st.file_uploader(
    "Upload een foto",
    type=["jpg", "jpeg", "png", "webp"]
)

def generate_pure_stretch_blocks(width, height, num_bands, split_complexity, seed=42):
    """
    Verdeelt het volledige canvas in een strak grid.
    Ieder blok krijgt een 100% horizontale stretch (slit-scan), geen 'normale' delen.
    """
    rng = np.random.default_rng(seed)
    blocks = []
    
    # 1. Bepaal horizontale banden (Verdiepingen)
    y_edges = [0]
    curr_y = 0
    while curr_y < height:
        step = max(2, int(rng.normal(height / num_bands, (height / num_bands) * 0.5)))
        curr_y += step
        if curr_y >= height - (height // 20): 
            break
        y_edges.append(curr_y)
    y_edges.append(height)
    
    # 2. Breek de banden op in verticale blokken
    for i in range(len(y_edges)-1):
        y1, y2 = y_edges[i], y_edges[i+1]
        
        x_edges = [0]
        curr_x = 0
        while curr_x < width:
            # Bepaal of deze band verder opgedeeld wordt
            if rng.random() < split_complexity:
                step = rng.integers(width // 15, width // 2)
                curr_x += step
                if curr_x >= width - (width // 20):
                    break
                x_edges.append(curr_x)
            else:
                break
        x_edges.append(width)
        
        # 3. Creëer de uiteindelijke stretch-blokken
        for j in range(len(x_edges)-1):
            x1, x2 = x_edges[j], x_edges[j+1]
            
            # Kies een willekeurig punt binnen (of vlak buiten) het blok om te samplen
            sample_x = rng.integers(0, width)
            
            blocks.append({
                'x1': x1, 'x2': x2, 
                'y1': y1, 'y2': y2,
                'base_x': sample_x,
                'phase': rng.random() * 2 * math.pi,
                'speed': rng.uniform(0.1, 1.0) * rng.choice([-1, 1])
            })
            
    return blocks

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
        st.subheader("⚙️ Grid Instellingen")
        
        col1, col2 = st.columns(2)
        with col1:
            num_bands = st.slider("Aantal Horizontale Banden", 20, 300, 100, help="Dikte van de horizontale strepen.")
        with col2:
            split_complexity = st.slider("Verticale Fragmentatie", 0.0, 1.0, 0.75, step=0.05, help="Hoeveel blokken er naast elkaar ontstaan.")
            
        seed_photo = st.number_input("Variatie Seed (voor een andere vlakverdeling)", value=42)

        if st.button("🖼️ Genereer Volledige Stretch", type="primary"):
            img_array = np.array(img, dtype=np.uint8)
            height, width, _ = img_array.shape
            
            blocks = generate_pure_stretch_blocks(width, height, num_bands, split_complexity, seed_photo)
            output_array = np.empty_like(img_array)
            
            # Pas de stretch toe op elk afzonderlijk blok
            for b in blocks:
                sx = np.clip(b['base_x'], 0, width - 1)
                source_col = img_array[b['y1']:b['y2'], sx:sx+1, :]
                output_array[b['y1']:b['y2'], b['x1']:b['x2'], :] = np.repeat(source_col, b['x2'] - b['x1'], axis=1)

            result_img = Image.fromarray(output_array)
            st.image(result_img, caption="100% Time Stretched", use_container_width=True)

            buf = io.BytesIO()
            result_img.save(buf, format="PNG")
            st.download_button(label="⬇️ Download High-Res PNG", data=buf.getvalue(), file_name="pure_stretch_style.png", mime="image/png")

    # =========================================
    # MODUS 2: VIDEO (MP4)
    # =========================================
    elif mode == "🎥 Geanimeerde Loop (MP4)":
        st.subheader("⚙️ Animatie Instellingen")
        
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            duration = st.selectbox("Duur (seconden)", [5, 10, 15], index=1)
            num_bands = st.slider("Aantal Horizontale Banden", 20, 300, 100)
        with col_v2:
            split_complexity = st.slider("Verticale Fragmentatie", 0.0, 1.0, 0.75, step=0.05)
            pan_speed = st.slider("Animatie Snelheid", 0.05, 1.0, 0.2)
            
        seed_vid = st.number_input("Variatie Seed", value=42, key="vid_seed")

        if st.button("🎬 Render Volledige Stretch Video", type="primary"):
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
            
            blocks = generate_pure_stretch_blocks(width, height, num_bands, split_complexity, seed_vid)
            
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
                    
                    for b in blocks:
                        # De sample verschuift soepel heen en weer per blok
                        offset = int(math.sin(t * pan_speed * b['speed'] + b['phase']) * (width * 0.15))
                        sx = np.clip(b['base_x'] + offset, 0, width - 1)
                        
                        source_col = img_array[b['y1']:b['y2'], sx:sx+1, :]
                        frame_buffer[b['y1']:b['y2'], b['x1']:b['x2'], :] = np.repeat(source_col, b['x2'] - b['x1'], axis=1)
                        
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
