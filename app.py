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
# 1. PAGINA SETUP & CSS (UI OPTIMALISATIE)
# =========================================
st.set_page_config(
    page_title="Ultimate Glitch & Stretch Studio",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stButton > button, .stDownloadButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        height: 3em;
        transition: all 0.3s ease;
        margin-top: 1rem;
    }
    .stButton > button:hover {
        transform: scale(1.02);
    }
    /* Minimalistische headers voor de expanders */
    .streamlit-expanderHeader {
        font-weight: bold;
        color: #555;
    }
    </style>
""", unsafe_allow_html=True)

# =========================================
# 2. KERN ALGORITMES
# =========================================
def generate_classic_glitch_data(width, height, bands_count, complexity_max, seed=42):
    rng = np.random.default_rng(seed)
    band_edges = np.linspace(0, height, bands_count + 1).astype(int)
    bands = []
    
    for i in range(bands_count):
        y1, y2 = band_edges[i], band_edges[i+1]
        if y2 <= y1: continue
            
        num_segments = rng.integers(1, complexity_max + 1)
        if num_segments == 1:
            splits = [0, width]
        else:
            split_points = sorted(rng.choice(np.arange(1, width), size=num_segments - 1, replace=False).tolist())
            splits = [0] + split_points + [width]
            
        segments = []
        for j in range(len(splits)-1):
            x1, x2 = splits[j], splits[j+1]
            sample_x = rng.integers(x1, x2)
            segments.append({'x1': x1, 'x2': x2, 'sample_x': sample_x})
            
        bands.append({
            'y1': y1, 'y2': y2,
            'segments': segments,
            'direction': rng.choice([-1, 1]),
            'cycles': rng.integers(1, 4),
            'phase': rng.random() * 2 * math.pi
        })
    return bands

def generate_repponen_grid_data(width, height, num_cols, base_rows, chaos_factor, brightness_var, seed=42):
    rng = np.random.default_rng(seed)
    blocks = []
    
    col_edges = [0]
    curr_x = 0
    while curr_x < width:
        variance = (width / num_cols) * chaos_factor
        step = max(5, int(rng.normal(width / num_cols, variance)))
        curr_x += step
        if curr_x >= width - 5: break
        col_edges.append(curr_x)
    col_edges.append(width)
    
    for i in range(len(col_edges)-1):
        x1, x2 = col_edges[i], col_edges[i+1]
        row_edges = [0]
        curr_y = 0
        target_rows = max(2, int(base_rows * rng.uniform(1.0 - chaos_factor, 1.0 + chaos_factor)))
        
        while curr_y < height:
            variance_y = (height / target_rows) * chaos_factor
            step = max(2, int(rng.normal(height / target_rows, variance_y)))
            curr_y += step
            if curr_y >= height - 2: break
            row_edges.append(curr_y)
        row_edges.append(height)
        
        for j in range(len(row_edges)-1):
            y1, y2 = row_edges[j], row_edges[j+1]
            sample_x = rng.integers(x1, x2)
            brightness = rng.uniform(1.0 - brightness_var, 1.0 + brightness_var) if brightness_var > 0 else 1.0
            
            blocks.append({
                'x1': x1, 'x2': x2, 'y1': y1, 'y2': y2,
                'sample_x': sample_x, 'brightness': brightness,
                'phase': rng.random() * 2 * math.pi,
                'speed': rng.uniform(0.1, 1.0) * rng.choice([-1, 1])
            })
    return blocks

# =========================================
# 3. SIDEBAR (GLOBALE PROJECT INSTELLINGEN)
# =========================================
with st.sidebar:
    st.title("🎛️ Studio Setup")
    st.markdown("Upload en selecteer je modus.")
    
    uploaded = st.file_uploader("1. Bestand", type=["jpg", "jpeg", "png", "webp"])
    stijl = st.selectbox("2. Ontwerpstijl", ["Classic Glitch (Vloeiend)", "Repponen Grid (Blokken)"])
    modus = st.radio("3. Output Formaat", ["🖼️ Statisch Kunstwerk", "🎥 Geanimeerde Loop"])
    st.markdown("---")
    st.caption("Gebruik de panelen in de hoofdweergave om parameters af te stellen.")

# =========================================
# 4. HOOFDSCHERM (INSPECTOR & CANVAS)
# =========================================
if uploaded:
    img = Image.open(uploaded).convert("RGB")
    
    # Verdeel het scherm in Controls (links) en Canvas (rechts)
    col_controls, col_canvas = st.columns([1, 2], gap="large")
    
    # -----------------------------------------
    # INSPECTOR (LINKER KOLOM)
    # -----------------------------------------
    with col_controls:
        st.subheader("⚙️ Parameters")
        
        # Specifieke controls per stijl
        if stijl == "Classic Glitch (Vloeiend)":
            bands_count = st.slider("Glitch Dichtheid (Banden)", 10, 200, 80)
            complexity = st.slider("Segment Complexiteit", 1, 8, 3)
            seed_val = st.number_input("Willekeurige Variatie (Seed)", value=42)
            if modus == "🎥 Geanimeerde Loop":
                anim_speed = st.slider("Animatie Snelheid", 1, 8, 3)
                
        elif stijl == "Repponen Grid (Blokken)":
            num_cols = st.slider("Verticale Kolommen", 2, 150, 40)
            base_rows = st.slider("Blokken per Kolom", 10, 300, 100)
            chaos = st.slider("Asymmetrie (Chaos)", 0.0, 0.8, 0.35, step=0.05)
            brightness = st.slider("Blok Contrast (Diepte)", 0.0, 0.5, 0.15, step=0.05)
            seed_val = st.number_input("Willekeurige Variatie (Seed)", value=99)
            if modus == "🎥 Geanimeerde Loop":
                anim_speed = st.slider("X-Ray Snelheid", 0.05, 2.0, 0.3)

        # Geavanceerde export instellingen in een expander om de UI clean te houden
        with st.expander("🛠️ Export & Render Instellingen", expanded=False):
            resolutie = st.selectbox("Resolutie", ["Origineel", "1920x1080 (Full HD)", "1280x720 (HD)"], index=0)
            if modus == "🎥 Geanimeerde Loop":
                duration = st.selectbox("Duur (seconden)", [5, 10, 15], index=1)
                fps = st.selectbox("Framerate", [24, 30, 60], index=1)
                
        render_btn = st.button(f"Genereer {modus.split(' ')[1]}", type="primary")

    # -----------------------------------------
    # CANVAS (RECHTER KOLOM)
    # -----------------------------------------
    with col_canvas:
        st.subheader("🖥️ Resultaat")
        
        with st.expander("📸 Bekijk originele afbeelding", expanded=False):
            st.image(img, use_container_width=True)
            st.caption(f"Actieve resolutie origineel: {img.width} x {img.height} pixels")
            
        # RENDER LOGICA
        if render_btn:
            with st.spinner("Bezig met renderen... Dit kan even duren."):
                target_img = img
                if resolutie != "Origineel":
                    tw, th = (1920, 1080) if "1920" in resolutie else (1280, 720)
                    sr, tr = img.width / img.height, tw / th
                    if sr > tr:
                        nw = int(img.height * tr)
                        target_img = img.crop(((img.width - nw)//2, 0, (img.width + nw)//2, img.height))
                    else:
                        nh = int(img.width / tr)
                        target_img = img.crop((0, (img.height - nh)//2, img.width, (img.height + nh)//2))
                    target_img = target_img.resize((tw, th), Image.Resampling.LANCZOS)
                    
                img_arr = np.array(target_img, dtype=np.uint8)
                h, w, _ = img_arr.shape

                # --- STATISCHE FOTO ---
                if modus == "🖼️ Statisch Kunstwerk":
                    out_arr = np.zeros_like(img_arr)
                    
                    if stijl == "Classic Glitch (Vloeiend)":
                        bands = generate_classic_glitch_data(w, h, bands_count, complexity, seed_val)
                        for b in bands:
                            for seg in b['segments']:
                                src = img_arr[b['y1']:b['y2'], seg['sample_x']:seg['sample_x']+1, :]
                                out_arr[b['y1']:b['y2'], seg['x1']:seg['x2'], :] = np.repeat(src, seg['x2']-seg['x1'], axis=1)
                    
                    elif stijl == "Repponen Grid (Blokken)":
                        blocks = generate_repponen_grid_data(w, h, num_cols, base_rows, chaos, brightness, seed_val)
                        for b in blocks:
                            sx = np.clip(b['sample_x'], b['x1'], b['x2'] - 1)
                            src = img_arr[b['y1']:b['y2'], sx:sx+1, :]
                            stretched = np.repeat(src, b['x2'] - b['x1'], axis=1)
                            if b['brightness'] != 1.0:
                                stretched = np.clip(stretched * b['brightness'], 0, 255).astype(np.uint8)
                            out_arr[b['y1']:b['y2'], b['x1']:b['x2'], :] = stretched
                            
                    res_img = Image.fromarray(out_arr)
                    st.image(res_img, use_container_width=True)
                    
                    buf = io.BytesIO()
                    res_img.save(buf, format="PNG")
                    st.download_button("⬇️ Download Resultaat (PNG)", buf.getvalue(), "studio_export.png", "image/png")

                # --- GEANIMEERDE VIDEO ---
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
                            pre_rows = []
                            for b in bands:
                                row = np.zeros((b['y2']-b['y1'], w, 3), dtype=np.uint8)
                                for seg in b['segments']:
                                    src = img_arr[b['y1']:b['y2'], seg['sample_x']:seg['sample_x']+1, :]
                                    row[:, seg['x1']:seg['x2'], :] = np.repeat(src, seg['x2']-seg['x1'], axis=1)
                                pre_rows.append(row)
                                
                            for frame in range(total_frames):
                                t = frame / fps
                                f_out = np.zeros_like(img_arr)
                                for idx, b in enumerate(bands):
                                    shift = int(math.sin(t * anim_speed * b['cycles'] + b['phase']) * (w * 0.1) * b['direction'])
                                    f_out[b['y1']:b['y2'], :, :] = np.roll(pre_rows[idx], shift, axis=1)
                                proc.stdin.write(f_out.tobytes())
                                if frame % 10 == 0: prog.progress(min(1.0, (frame+1)/total_frames))
                                
                        elif stijl == "Repponen Grid (Blokken)":
                            blocks = generate_repponen_grid_data(w, h, num_cols, base_rows, chaos, brightness, seed_val)
                            f_out = np.empty_like(img_arr)
                            
                            for frame in range(total_frames):
                                t = frame / fps
                                for b in blocks:
                                    bw = b['x2'] - b['x1']
                                    offset = int(math.sin(t * anim_speed * b['speed'] + b['phase']) * (bw / 2.5))
                                    sx = np.clip(b['sample_x'] + offset, b['x1'], b['x2'] - 1)
                                    src = img_arr[b['y1']:b['y2'], sx:sx+1, :]
                                    stretched = np.repeat(src, bw, axis=1)
                                    if b['brightness'] != 1.0:
                                        stretched = np.clip(stretched * b['brightness'], 0, 255).astype(np.uint8)
                                    f_out[b['y1']:b['y2'], b['x1']:b['x2'], :] = stretched
                                    
                                proc.stdin.write(f_out.tobytes())
                                if frame % 10 == 0: 
                                    prog.progress(min(1.0, (frame+1)/total_frames))
                                    gc.collect()

                        proc.stdin.close()
                        proc.wait()
                    except Exception:
                        proc.kill()
                        raise
                    
                    prog.progress(1.0)
                    with open(tmp.name, "rb") as f: st.video(f.read())
                    st.success("✅ Video succesvol gerenderd!")
                    
else:
    st.info("👋 Welkom! Upload een foto in de zijbalk om te beginnen.")
