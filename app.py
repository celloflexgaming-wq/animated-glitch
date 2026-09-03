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
    page_title="Repponen True Slit-Scan Studio",
    layout="centered"
)

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

st.title("🏙️ True Time-Stretch Studio")
st.markdown("*De authentieke Anton Repponen methode: Intacte focus-objecten met rand-extrusie.*")

uploaded = st.file_uploader("Upload een foto", type=["jpg", "jpeg", "png", "webp"])

def generate_true_repponen(img_array, num_bands, num_objects, min_size, max_size, seed=42):
    rng = np.random.default_rng(seed)
    height, width, _ = img_array.shape
    
    # 1. Genereer maskers (de intacte objecten zoals borden, gebouwen, pilaren)
    objects = []
    for _ in range(num_objects):
        # Variatie in objecten: pilaren (smal/hoog) vs gebouwen (breed)
        if rng.random() > 0.5:
            w = rng.integers(int(width * (min_size/2)), max(2, int(width * (max_size/3))))
            h = rng.integers(int(height * min_size), max(2, int(height * max_size)))
        else:
            w = rng.integers(int(width * min_size), max(2, int(width * max_size)))
            h = rng.integers(int(height * (min_size/2)), max(2, int(height * (max_size/3))))
            
        x = rng.integers(0, max(1, width - w))
        y = rng.integers(0, max(1, height - h))
        objects.append((x, y, w, h))
        
    # 2. Genereer horizontale banden (strepen)
    y_edges = [0]
    curr_y = 0
    while curr_y < height:
        step = rng.integers(2, max(4, height // (num_bands // 2)))
        curr_y += step
        if curr_y >= height - 2: 
            break
        y_edges.append(curr_y)
    y_edges.append(height)
    
    output = np.zeros_like(img_array)
    band_data = [] # Voor animatie
    
    # 3. Vul elke horizontale band in
    for i in range(len(y_edges)-1):
        y1, y2 = y_edges[i], y_edges[i+1]
        
        intersecting = []
        for (ox, oy, ow, oh) in objects:
            if oy < y2 and (oy + oh) > y1:
                intersecting.append((ox, ox + ow))
                
        if not intersecting:
            sample_x = rng.integers(0, width)
            output[y1:y2, :, :] = np.repeat(img_array[y1:y2, sample_x:sample_x+1, :], width, axis=1)
            band_data.append({'type': 'bg', 'y1': y1, 'y2': y2, 'sample_x': sample_x, 
                              'phase': rng.random()*2*math.pi, 'speed': rng.uniform(0.1, 0.5)*rng.choice([-1,1])})
        else:
            intersecting.sort()
            merged = []
            for obj in intersecting:
                if not merged:
                    merged.append(obj)
                else:
                    last = merged[-1]
                    if obj[0] <= last[1]:
                        merged[-1] = (last[0], max(last[1], obj[1]))
                    else:
                        merged.append(obj)
                        
            curr_x = 0
            obj_meta = []
            for (ox1, ox2) in merged:
                if ox1 > curr_x:
                    output[y1:y2, curr_x:ox1, :] = np.repeat(img_array[y1:y2, ox1:ox1+1, :], ox1 - curr_x, axis=1)
                output[y1:y2, ox1:ox2, :] = img_array[y1:y2, ox1:ox2, :]
                curr_x = ox2
                obj_meta.append((ox1, ox2))
                
            if curr_x < width:
                output[y1:y2, curr_x:width, :] = np.repeat(img_array[y1:y2, curr_x-1:curr_x, :], width - curr_x, axis=1)
                
            band_data.append({'type': 'fg', 'y1': y1, 'y2': y2, 'objs': obj_meta,
                              'phase': rng.random()*2*math.pi, 'speed': rng.uniform(0.05, 0.3)*rng.choice([-1,1])})
                              
    return output, band_data

if uploaded:
    img = Image.open(uploaded).convert("RGB")
    st.image(img, caption="Originele foto", use_container_width=True)
    st.markdown("---")
    
    mode = st.radio("Output Formaat:", ["🖼️ Statisch Kunstwerk", "🎥 Geanimeerde Loop (MP4)"], horizontal=True)
    st.markdown("---")

    if mode == "🖼️ Statisch Kunstwerk":
        st.subheader("⚙️ Masker & Extrusie Instellingen")
        col1, col2 = st.columns(2)
        with col1:
            num_bands = st.slider("Aantal Achtergrond Strepen", 50, 300, 150)
            num_objects = st.slider("Aantal Intacte Objecten", 1, 30, 8, help="Hoeveel gebouwen of borden blijven staan.")
        with col2:
            min_size = st.slider("Minimale Object Grootte (%)", 1, 20, 5) / 100.0
            max_size = st.slider("Maximale Object Grootte (%)", 10, 80, 35) / 100.0
            seed_photo = st.number_input("Architecturale Variatie (Seed)", value=42)

        if st.button("🖼️ Genereer Masterpiece", type="primary"):
            img_array = np.array(img, dtype=np.uint8)
            output_array, _ = generate_true_repponen(img_array, num_bands, num_objects, min_size, max_size, seed_photo)
            
            result_img = Image.fromarray(output_array)
            st.image(result_img, caption="True Time-Stretched", use_container_width=True)
            
            buf = io.BytesIO()
            result_img.save(buf, format="PNG", optimize=True)
            st.download_button(label="⬇️ Download High-Res PNG", data=buf.getvalue(), file_name="true_repponen.png", mime="image/png")

    elif mode == "🎥 Geanimeerde Loop (MP4)":
        st.subheader("⚙️ Animatie Instellingen")
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            duration = st.selectbox("Duur (seconden)", [5, 10, 15], index=1)
            num_bands = st.slider("Aantal Achtergrond Strepen", 50, 300, 150)
            num_objects = st.slider("Aantal Intacte Objecten", 1, 30, 8)
        with col_v2:
            pan_speed = st.slider("Animatie Snelheid", 0.05, 1.0, 0.2)
            min_size = st.slider("Minimale Object Grootte (%)", 1, 20, 5) / 100.0
            max_size = st.slider("Maximale Object Grootte (%)", 10, 80, 35) / 100.0
            seed_vid = st.number_input("Architecturale Variatie (Seed)", value=42, key="vid_seed")

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
            
            _, band_data = generate_true_repponen(img_array, num_bands, num_objects, min_size, max_size, seed_vid)
            
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
                        if b['type'] == 'bg':
                            offset = int(math.sin(t * pan_speed * b['speed'] + b['phase']) * (width * 0.2))
                            sx = np.clip(b['sample_x'] + offset, 0, width - 1)
                            frame_buffer[b['y1']:b['y2'], :, :] = np.repeat(img_array[b['y1']:b['y2'], sx:sx+1, :], width, axis=1)
                        else:
                            y1, y2 = b['y1'], b['y2']
                            curr_x = 0
                            for (ox1, ox2) in b['objs']:
                                offset = int(math.sin(t * pan_speed * b['speed'] + b['phase']) * (width * 0.05))
                                n_ox1 = np.clip(ox1 + offset, 1, width - 2)
                                n_ox2 = np.clip(ox2 + offset, n_ox1 + 1, width - 1)
                                
                                if n_ox1 > curr_x:
                                    frame_buffer[y1:y2, curr_x:n_ox1, :] = np.repeat(img_array[y1:y2, n_ox1:n_ox1+1, :], n_ox1 - curr_x, axis=1)
                                frame_buffer[y1:y2, n_ox1:n_ox2, :] = img_array[y1:y2, n_ox1:n_ox2, :]
                                curr_x = n_ox2
                                
                            if curr_x < width:
                                frame_buffer[y1:y2, curr_x:width, :] = np.repeat(img_array[y1:y2, curr_x-1:curr_x, :], width - curr_x, axis=1)
                                
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

