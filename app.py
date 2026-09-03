import streamlit as st
import numpy as np
from PIL import Image
import subprocess
import tempfile
import os
import math
import io
import gc

# =========================================
# 1. WORKSPACE SETUP
# =========================================
st.set_page_config(page_title="Ultimate Motion Glitch Studio", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 6px; font-weight: bold; height: 3em; transition: 0.2s; }
    .stButton > button:hover { transform: scale(1.02); border-color: #6EFF6A; color: #6EFF6A; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    </style>
""", unsafe_allow_html=True)

# =========================================
# 2. RENDER ENGINES
# =========================================
def generate_classic_glitch_data(width, height, bands_count, complexity_max, seed=42):
    rng = np.random.default_rng(seed)
    band_edges = np.linspace(0, height, bands_count + 1).astype(int)
    bands = []
    
    for i in range(bands_count):
        y1, y2 = band_edges[i], band_edges[i+1]
        if y2 <= y1: continue
            
        num_segments = rng.integers(1, complexity_max + 1)
        splits = [0, width] if num_segments == 1 else [0] + sorted(rng.choice(np.arange(1, width), size=num_segments - 1, replace=False).tolist()) + [width]
            
        segments = [{'x1': splits[j], 'x2': splits[j+1], 'sample_x': rng.integers(splits[j], splits[j+1])} for j in range(len(splits)-1)]
            
        bands.append({
            'y1': y1, 'y2': y2, 'segments': segments,
            'direction': rng.choice([-1, 1]), 'cycles': rng.integers(1, 4), 'phase': rng.random() * 2 * math.pi
        })
    return bands

def generate_repponen_grid_data(width, height, num_cols, base_rows, chaos_factor, brightness_var, seed=42):
    rng = np.random.default_rng(seed)
    blocks, col_edges, curr_x = [], [0], 0
    
    while curr_x < width:
        curr_x += max(5, int(rng.normal(width / num_cols, (width / num_cols) * chaos_factor)))
        if curr_x >= width - 5: break
        col_edges.append(curr_x)
    col_edges.append(width)
    
    for i in range(len(col_edges)-1):
        x1, x2 = col_edges[i], col_edges[i+1]
        row_edges, curr_y = [0], 0
        target_rows = max(2, int(base_rows * rng.uniform(1.0 - chaos_factor, 1.0 + chaos_factor)))
        
        while curr_y < height:
            curr_y += max(2, int(rng.normal(height / target_rows, (height / target_rows) * chaos_factor)))
            if curr_y >= height - 2: break
            row_edges.append(curr_y)
        row_edges.append(height)
        
        for j in range(len(row_edges)-1):
            blocks.append({
                'x1': x1, 'x2': x2, 'y1': row_edges[j], 'y2': row_edges[j+1],
                'sample_x': rng.integers(x1, x2),
                'brightness': rng.uniform(1.0 - brightness_var, 1.0 + brightness_var) if brightness_var > 0 else 1.0,
                'phase': rng.random() * 2 * math.pi,
                'speed': rng.uniform(0.1, 1.0) * rng.choice([-1, 1])
            })
    return blocks

# =========================================
# 3. SIDEBAR (PROJECT INSTELLINGEN)
# =========================================
with st.sidebar:
    st.title("🎛️ Project Setup")
    uploaded = st.file_uploader("1. Media", type=["jpg", "jpeg", "png", "webp"])
    stijl = st.selectbox("2. Engine", ["Classic Glitch (Vloeiend)", "Repponen Grid (Blokken)"])
    modus = st.radio("3. Output Type", ["🖼️ Statisch Beeld", "🎥 Motion (MP4)"])

# =========================================
# 4. HOOFDSCHERM
# =========================================
if uploaded:
    img = Image.open(uploaded).convert("RGB")
    col_controls, col_canvas = st.columns([1.2, 2], gap="large")
    
    # --- INSPECTOR PANEEL ---
    with col_controls:
        # TABS VOOR OVERZICHTELIJKHEID
        tab_design, tab_motion, tab_render = st.tabs(["🎨 Vormgeving", "🎞️ Motion", "⚙️ Export"])
        
        with tab_design:
            st.subheader("Look & Feel")
            if stijl == "Classic Glitch (Vloeiend)":
                bands_count = st.slider("Glitch Dichtheid", 10, 300, 100)
                complexity = st.slider("Segment Complexiteit", 1, 10, 4)
            else:
                num_cols = st.slider("Verticale Kolommen", 2, 150, 40)
                base_rows = st.slider("Horizontale Rijen", 10, 300, 100)
                chaos = st.slider("Asymmetrie (Chaos)", 0.0, 0.8, 0.35, step=0.05)
                brightness = st.slider("Blok Contrast", 0.0, 0.5, 0.15, step=0.05)
            seed_val = st.number_input("Variatie Seed", value=42)

        with tab_motion:
            if modus == "🎥 Motion (MP4)":
                st.subheader("Animatie Dynamiek")
                anim_speed = st.slider("Globale Snelheid", 0.05, 5.0, 1.0, step=0.05, help="Snelheid van de golven en verschuivingen.")
                duration = st.select_slider("Duur (seconden)", options=[5, 10, 15, 30, 45, 60], value=10)
            else:
                st.info("Schakel over naar 'Motion (MP4)' in de zijbalk om animaties in te stellen.")

        with tab_render:
            st.subheader("Output Kwaliteit")
            resolutie = st.selectbox("Resolutie", ["Origineel", "1920x1080 (Full HD)", "1280x720 (HD)"], index=0)
            if modus == "🎥 Motion (MP4)":
                fps = st.selectbox("Framerate", [24, 30, 60], index=1)
                
        render_btn = st.button("🚀 Start Render Queue", type="primary")

    # --- CANVAS PANEEL ---
    with col_canvas:
        with st.expander("📸 Bekijk bronbestand", expanded=False):
            st.image(img, use_container_width=True)
            
        if render_btn:
            with st.spinner("Bezig met renderen... Dit kan even duren bij video's tot 60 seconden."):
                target_img = img
                if resolutie != "Origineel":
                    tw, th = (1920, 1080) if "1920" in resolutie else (1280, 720)
                    sr, tr = img.width / img.height, tw / th
                    if sr > tr: target_img = img.crop(((img.width - int(img.height * tr))//2, 0, (img.width + int(img.height * tr))//2, img.height))
                    else: target_img = img.crop((0, (img.height - int(img.width / tr))//2, img.width, (img.height + int(img.width / tr))//2))
                    target_img = target_img.resize((tw, th), Image.Resampling.LANCZOS)
                    
                img_arr = np.array(target_img, dtype=np.uint8)
                h, w, _ = img_arr.shape

                # --- STATISCHE RENDER ---
                if modus == "🖼️ Statisch Beeld":
                    out_arr = np.empty_like(img_arr)
                    if stijl == "Classic Glitch (Vloeiend)":
                        bands = generate_classic_glitch_data(w, h, bands_count, complexity, seed_val)
                        for b in bands:
                            for seg in b['segments']:
                                src = img_arr[b['y1']:b['y2'], seg['sample_x']:seg['sample_x']+1, :]
                                out_arr[b['y1']:b['y2'], seg['x1']:seg['x2'], :] = np.repeat(src, seg['x2']-seg['x1'], axis=1)
                    else:
                        blocks = generate_repponen_grid_data(w, h, num_cols, base_rows, chaos, brightness, seed_val)
                        for b in blocks:
                            sx = np.clip(b['sample_x'], b['x1'], b['x2'] - 1)
                            stretched = np.repeat(img_arr[b['y1']:b['y2'], sx:sx+1, :], b['x2'] - b['x1'], axis=1)
                            if b['brightness'] != 1.0: stretched = np.clip(stretched * b['brightness'], 0, 255).astype(np.uint8)
                            out_arr[b['y1']:b['y2'], b['x1']:b['x2'], :] = stretched
                            
                    res_img = Image.fromarray(out_arr)
                    st.image(res_img, use_container_width=True)
                    buf = io.BytesIO()
                    res_img.save(buf, format="PNG")
                    st.download_button("⬇️ Download PNG", buf.getvalue(), "studio_export.png", "image/png")

                # --- VIDEO RENDER ---
                else:
                    total_frames = duration * fps
                    prog = st.progress(0)
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                    tmp.close()
                    
                    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-vcodec", "rawvideo", 
                           "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", 
                           "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p", tmp.name]
                    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
                    
                    try:
                        if stijl == "Classic Glitch (Vloeiend)":
                            bands = generate_classic_glitch_data(w, h, bands_count, complexity, seed_val)
                            pre_rows = [np.zeros((b['y2']-b['y1'], w, 3), dtype=np.uint8) for b in bands]
                            for idx, b in enumerate(bands):
                                for seg in b['segments']:
                                    pre_rows[idx][:, seg['x1']:seg['x2'], :] = np.repeat(img_arr[b['y1']:b['y2'], seg['sample_x']:seg['sample_x']+1, :], seg['x2']-seg['x1'], axis=1)
                                    
                            for frame in range(total_frames):
                                t = frame / fps
                                f_out = np.empty_like(img_arr)
                                for idx, b in enumerate(bands):
                                    shift = int(math.sin(t * anim_speed * b['cycles'] + b['phase']) * (w * 0.1) * b['direction'])
                                    f_out[b['y1']:b['y2'], :, :] = np.roll(pre_rows[idx], shift, axis=1)
                                proc.stdin.write(f_out.tobytes())
                                if frame % (fps // 2) == 0: prog.progress(min(1.0, (frame+1)/total_frames))
                                
                        else:
                            blocks = generate_repponen_grid_data(w, h, num_cols, base_rows, chaos, brightness, seed_val)
                            f_out = np.empty_like(img_arr)
                            
                            for frame in range(total_frames):
                                t = frame / fps
                                for b in blocks:
                                    bw = b['x2'] - b['x1']
                                    offset = int(math.sin(t * anim_speed * b['speed'] + b['phase']) * (bw / 2.5))
                                    sx = np.clip(b['sample_x'] + offset, b['x1'], b['x2'] - 1)
                                    stretched = np.repeat(img_arr[b['y1']:b['y2'], sx:sx+1, :], bw, axis=1)
                                    if b['brightness'] != 1.0: stretched = np.clip(stretched * b['brightness'], 0, 255).astype(np.uint8)
                                    f_out[b['y1']:b['y2'], b['x1']:b['x2'], :] = stretched
                                    
                                proc.stdin.write(f_out.tobytes())
                                if frame % (fps // 2) == 0: 
                                    prog.progress(min(1.0, (frame+1)/total_frames))
                                    gc.collect()

                        proc.stdin.close()
                        proc.wait()
                    except Exception:
                        proc.kill()
                        raise
                    
                    prog.progress(1.0)
                    with open(tmp.name, "rb") as f: st.video(f.read())
                    st.success("✅ Render Voltooid!")
else:
    st.info("👋 Upload media in het projectpaneel om te starten.")
