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
    page_title="Grid Scatter Studio",
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

st.title("🧩 The Grid Scatter Studio")
st.markdown("*Geavanceerde architecturale fragmentatie met willekeurige spreiding en diepte.*")

uploaded = st.file_uploader(
    "Upload een foto",
    type=["jpg", "jpeg", "png", "webp"]
)

def generate_scatter_blocks(width, height, num_cols, base_rows, chaos_factor, glitch_chance, brightness_var, seed=42):
    """
    Genereert het grid en bepaalt per blok de eigenschappen (glitch of origineel, helderheid).
    """
    rng = np.random.default_rng(seed)
    blocks = []
    
    # 1. Verticale kolommen
    col_edges = [0]
    curr_x = 0
    while curr_x < width:
        variance = (width / num_cols) * chaos_factor
        step = max(5, int(rng.normal(width / num_cols, variance)))
        curr_x += step
        if curr_x >= width - 5: 
            break
        col_edges.append(curr_x)
    col_edges.append(width)
    
    # 2. Horizontale rijen per kolom
    for i in range(len(col_edges)-1):
        x1, x2 = col_edges[i], col_edges[i+1]
        
        row_edges = [0]
        curr_y = 0
        target_rows = max(2, int(base_rows * rng.uniform(1.0 - chaos_factor, 1.0 + chaos_factor)))
        
        while curr_y < height:
            variance_y = (height / target_rows) * chaos_factor
            step = max(2, int(rng.normal(height / target_rows, variance_y)))
            curr_y += step
            if curr_y >= height - 2: 
                break
            row_edges.append(curr_y)
        row_edges.append(height)
        
        # 3. Blokken vullen
        for j in range(len(row_edges)-1):
            y1, y2 = row_edges[j], row_edges[j+1]
            
            is_glitch = rng.random() < glitch_chance
            sample_x = rng.integers(x1, x2)
            
            # Subtiele belichtingsverschillen voor meer diepte tussen de blokken
            brightness = 1.0
            if is_glitch and brightness_var > 0:
                brightness = rng.uniform(1.0 - brightness_var, 1.0 + brightness_var)
            
            blocks.append({
                'x1': x1, 'x2': x2, 
                'y1': y1, 'y2': y2,
                'is_glitch': is_glitch,
                'sample_x': sample_x,
                'brightness': brightness,
                'phase': rng.random() * 2 * math.pi,
                'speed': rng.uniform(0.1, 1.0) * rng.choice([-1, 1])
            })
            
    return blocks

if uploaded:
    img = Image.open(uploaded).convert("RGB")
    st.image(img, caption="Originele foto", use_container_width=True)
    st.markdown("---")
    
    mode = st.radio("Output Formaat:", ["🖼️ Statisch Grid", "🎥 Geanimeerde Loop (MP4)"], horizontal=True)
    st.markdown("---")

    # =========================================
    # MODUS 1: STATISCHE FOTO
    # =========================================
    if mode == "🖼️ Statisch Grid":
        st.subheader("⚙️ Vorm & Structuur")
        col1, col2 = st.columns(2)
        with col1:
            num_cols = st.slider("Aantal Kolommen", 2, 100, 25)
            base_rows = st.slider("Aantal Blokken per Kolom", 5, 200, 60)
            chaos_factor = st.slider("Asymmetrie (Chaos)", 0.0, 0.8, 0.4, step=0.05)
        with col2:
            st.markdown("### 🎨 Glitch Stijl")
            glitch_chance = st.slider("Glitch Dekking (%)", 0, 100, 65, help="Hoeveel blokken worden gestretcht? 100% is het volledige Repponen-effect.") / 100.0
            brightness_var = st.slider("Blok Contrast/Belichting", 0.0, 0.5, 0.15, step=0.05, help="Maakt abstracte blokken willekeurig lichter of donkerder voor een 3D pop.")
            seed_photo = st.number_input("Willekeurige Verspreiding (Seed)", value=77)

        if st.button("🖼️ Genereer Scattered Masterpiece", type="primary"):
            img_array = np.array(img, dtype=np.uint8)
            height, width, _ = img_array.shape
            
            blocks = generate_scatter_blocks(width, height, num_cols, base_rows, chaos_factor, glitch_chance, brightness_var, seed_photo)
            output_array = np.empty_like(img_array)
            
            for b in blocks:
                if b['is_glitch']:
                    # Pas de stretch en belichting toe
                    sx = np.clip(b['sample_x'], b['x1'], b['x2'] - 1)
                    source_col = img_array[b['y1']:b['y2'], sx:sx+1, :]
                    stretched = np.repeat(source_col, b['x2'] - b['x1'], axis=1)
                    
                    if b['brightness'] != 1.0:
                        stretched = np.clip(stretched * b['brightness'], 0, 255).astype(np.uint8)
                    
                    output_array[b['y1']:b['y2'], b['x1']:b['x2'], :] = stretched
                else:
                    # Behoud de originele fotopixels strak in het grid
                    output_array[b['y1']:b['y2'], b['x1']:b['x2'], :] = img_array[b['y1']:b['y2'], b['x1']:b['x2'], :]

            result_img = Image.fromarray(output_array)
            st.image(result_img, caption="Scattered Glitch Resultaat", use_container_width=True)

            buf = io.BytesIO()
            result_img.save(buf, format="PNG", optimize=True)
            st.download_button(label="⬇️ Download High-Res PNG", data=buf.getvalue(), file_name="scatter_glitch.png", mime="image/png")

    # =========================================
    # MODUS 2: VIDEO (MP4)
    # =========================================
    elif mode == "🎥 Geanimeerde Loop (MP4)":
        st.subheader("⚙️ Animatie & Structuur")
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            duration = st.selectbox("Duur (seconden)", [5, 10, 15], index=1)
            num_cols = st.slider("Aantal Kolommen", 2, 100, 25)
            base_rows = st.slider("Aantal Blokken per Kolom", 5, 200, 60)
            chaos_factor = st.slider("Asymmetrie (Chaos)", 0.0, 0.8, 0.4, step=0.05)
        with col_v2:
            glitch_chance = st.slider("Glitch Dekking (%)", 0, 100, 65) / 100.0
            brightness_var = st.slider("Blok Contrast/Belichting", 0.0, 0.5, 0.15, step=0.05)
            pan_speed = st.slider("Animatie Snelheid", 0.05, 2.0, 0.4)
            seed_vid = st.number_input("Willekeurige Verspreiding (Seed)", value=77, key="vid_seed")

        if st.button("🎬 Render Scattered Animatie", type="primary"):
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
            
            blocks = generate_scatter_blocks(width, height, num_cols, base_rows, chaos_factor, glitch_chance, brightness_var, seed_vid)
            
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
                        if b['is_glitch']:
                            block_width = b['x2'] - b['x1']
                            offset = int(math.sin(t * pan_speed * b['speed'] + b['phase']) * (block_width / 2.5))
                            sx = np.clip(b['sample_x'] + offset, b['x1'], b['x2'] - 1)
                            
                            source_col = img_array[b['y1']:b['y2'], sx:sx+1, :]
                            stretched = np.repeat(source_col, block_width, axis=1)
                            
                            if b['brightness'] != 1.0:
                                stretched = np.clip(stretched * b['brightness'], 0, 255).astype(np.uint8)
                            
                            frame_buffer[b['y1']:b['y2'], b['x1']:b['x2'], :] = stretched
                        else:
                            # Originele blokken blijven strak op hun plaats
                            frame_buffer[b['y1']:b['y2'], b['x1']:b['x2'], :] = img_array[b['y1']:b['y2'], b['x1']:b['x2'], :]
                            
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
