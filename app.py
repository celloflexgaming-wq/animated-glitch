import streamlit as st
import numpy as np
from PIL import Image
import subprocess
import tempfile
import os
import math
import io

# Setup van de pagina
st.set_page_config(
    page_title="Time Stretch Studio (Anton Repponen Stijl)",
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

st.title("🎞️ Time Stretch Studio (Anton Repponen Stijl)")

uploaded = st.file_uploader(
    "Upload een foto",
    type=["jpg", "jpeg", "png", "webp"]
)

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
        ["🎥 Time Stretch Video (Moving Mosaic)", "🖼️ Time Stretch Foto (Static Mosaic)"],
        horizontal=True
    )
    st.markdown("---")

    # =========================================
    # MODUS 1: STATISCHE TIME STRETCH FOTO (Static Mosaic)
    # =========================================
    if mode == "🖼️ Time Stretch Foto (Static Mosaic)":
        st.subheader("⚙️ Foto-instellingen")

        resolution_photo = st.selectbox(
            "Foto resolutie",
            [
                "1920 × 1080 — Full HD",
                "1280 × 720 — HD",
                "Originele beeldverhouding behouden"
            ],
            index=0
        )

        num_variations_photo = st.slider(
            "Aantal gesimuleerde frames (Variaties voor mozaïek)",
            5,
            20,
            10,
            key="photo_variations"
        )
        
        scanline_orientation_photo = st.radio(
            "Scanline Oriëntatie",
            ["Horizontaal", "Verticaal"],
            index=1,
            key="photo_orientation"
        )

        variation_type_photo = st.radio(
            "Variatie Type",
            ["Kleurverschuiving"],
            index=0,
            key="photo_var_type"
        )

        # De 'glitch banden' sliders zijn vervangen door een inherent concept van 1-pixel scanlines.

        if st.button("🖼️ Genereer Time Stretch Foto", type="primary"):
            # Resolutie en crop logica (behouden)
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

            # --- NIEUWE LOGICA VOOR TIME STRETCH FOTO ---
            img_array = np.array(img, dtype=np.uint8)
            height, width, _ = img_array.shape
            
            # Stap 1: Genereer N gesimuleerde frames door middel van kleurverschuiving
            variations = []
            if variation_type_photo == "Kleurverschuiving":
                for _ in range(num_variations_photo):
                    # Simuleer variatie door elke pixel te vermenigvuldigen met een willekeurige kleur
                    color_shift = np.random.uniform(0.8, 1.2, (1, 1, 3))
                    varied = (img_array * color_shift).clip(0, 255).astype(np.uint8)
                    variations.append(varied)
            
            # Stap 2: Pas een pixel-brede stretch toe op elk frame om de basis-textuur te creëren
            # Elke horizontale scanline wordt nu een 1-pixel-brede stretched blok.
            pre_stretched_variations = []
            for v in variations:
                v_h, v_w, _ = v.shape
                # We passen horizontalen stretch toe op 1-pixel banden.
                stretched_frame = np.zeros_like(v)
                for y in range(v_h):
                    sample_x = np.random.randint(0, v_w)
                    single_pixel_column = v[y:y+1, sample_x:sample_x+1, :]
                    stretched_frame[y, :, :] = np.repeat(single_pixel_column, v_w, axis=1)
                pre_stretched_variations.append(stretched_frame)
            
            # Stap 3: Creëer het uiteindelijke mozaïek door scanlines van de andere oriëntatie te samplen
            output_array = np.zeros_like(img_array)
            if scanline_orientation_photo == "Verticaal":
                # Mozaïek van verticale scanlines (meest vergelijkbaar met de voorbeelden)
                for x in range(width):
                    # Kies het gesimuleerde frame op basis van de positie (modulo)
                    frame_idx = x % num_variations_photo
                    sample_stretched_v = pre_stretched_variations[frame_idx]
                    
                    # Sample die specifieke verticale kolom en paste hem
                    sample_column = sample_stretched_v[:, x, :]
                    output_array[:, x, :] = sample_column
            else:
                # Mozaïek van horizontale scanlines
                for y in range(height):
                    frame_idx = y % num_variations_photo
                    sample_stretched_h = pre_stretched_variations[frame_idx]
                    
                    sample_row = sample_stretched_h[y, :, :]
                    output_array[y, :, :] = sample_row

            result_img = Image.fromarray(output_array)
            st.image(result_img, caption="Gegenereerde Time Stretch Foto (Static Mosaic)", use_container_width=True)

            buf = io.BytesIO()
            result_img.save(buf, format="PNG")
            st.download_button(
                label="⬇️ Download Time Stretch Foto (PNG)",
                data=buf.getvalue(),
                file_name="time_stretch_foto.png",
                mime="image/png"
            )

    # =========================================
    # MODUS 2: TIME STRETCH VIDEO (MP4, Moving Mosaic)
    # =========================================
    elif mode == "🎥 Time Stretch Video (Moving Mosaic)":
        st.subheader("⚙️ Video-instellingen")

        resolution = st.selectbox(
            "Videoresolutie",
            [
                "1920 × 1080 — Full HD",
                "1280 × 720 — HD"
            ],
            index=0
        )

        if resolution.startswith("1920"):
            target_width = 1920
            target_height = 1080
        else:
            target_width = 1280
            target_height = 720

        duration = st.selectbox(
            "Duur (seconden)",
            [5, 10, 15, 20, 30],
            index=1
        )

        fps = st.selectbox(
            "FPS",
            [24, 30, 60],
            index=1
        )

        quality = st.selectbox(
            "Videokwaliteit",
            [
                "Maximale kwaliteit",
                "Zeer hoge kwaliteit",
                "Hoge kwaliteit"
            ],
            index=0
        )

        if quality == "Maximale kwaliteit":
            crf = 12
            preset = "slow"
        elif quality == "Zeer hoge kwaliteit":
            crf = 16
            preset = "medium"
        else:
            crf = 20
            preset = "medium"

        num_variations_video = st.slider(
            "Aantal gesimuleerde frames (Variaties voor mozaïek)",
            5,
            20,
            10,
            key="video_variations"
        )
        
        mosaic_orientation_video = st.radio(
            "Mosaic Oriëntatie",
            ["Horizontaal", "Verticaal"],
            index=1,
            key="video_mosaic_orientation"
        )

        # De 'glitch banden', 'complexiteit' en 'snelheid' sliders zijn vervangen door deze logica.

        if st.button("🎬 Maak Full HD Time Stretch video", type="primary"):
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

            img = img.resize(
                (target_width, target_height),
                Image.Resampling.LANCZOS
            )

            img_array = np.array(img, dtype=np.uint8)
            height, width, channels = img_array.shape
            total_frames = int(duration * fps)

            st.write(f"**Resolutie:** {width} × {height}")
            st.write(f"**Frames:** {total_frames}")
            st.write(f"**Kwaliteit:** CRF {crf} / {preset}")

            # --- NIEUWE LOGICA VOOR TIME STRETCH VIDEO ---
            
            # Stap 1: Pre-genereer N gesimuleerde frames (variaties) door kleurverschuiving
            # We gebruiken dezelfde logica als bij de foto.
            variations = []
            for _ in range(num_variations_video):
                color_shift = np.random.uniform(0.8, 1.2, (1, 1, 3))
                varied = (img_array * color_shift).clip(0, 255).astype(np.uint8)
                variations.append(varied)
            
            # Stap 2: Pre-genereer pre-stretched basistextuur voor elk frame
            pre_stretched_variations = []
            for v in variations:
                v_h, v_w, _ = v.shape
                stretched_frame = np.zeros_like(v)
                for y in range(v_h):
                    sample_x = np.random.randint(0, v_w)
                    single_pixel_column = v[y:y+1, sample_x:sample_x+1, :]
                    stretched_frame[y, :, :] = np.repeat(single_pixel_column, v_w, axis=1)
                pre_stretched_variations.append(stretched_frame)

            progress = st.progress(0)
            output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            output_path = output_file.name
            output_file.close()

            command = [
                "ffmpeg",
                "-y",
                "-loglevel", "error",
                "-f", "rawvideo",
                "-vcodec", "rawvideo",
                "-pix_fmt", "rgb24",
                "-s", f"{width}x{height}",
                "-r", str(fps),
                "-i", "-",
                "-an",
                "-c:v", "libx264",
                "-preset", preset,
                "-crf", str(crf),
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                output_path
            ]

            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            try:
                # Stap 3: Genereer de video frame voor frame met een gedetailleerd rollend mozaïek
                for frame_number in range(total_frames):
                    t = frame_number / fps
                    frame_out = np.zeros_like(img_array)

                    if mosaic_orientation_video == "Verticaal":
                        # Verticaal mosaic dat rollend wordt gevormd
                        for x in range(width):
                            # Het frame-nummer wordt toegevoegd aan de modulo om de animatie te creëren
                            frame_idx = (x + frame_number) % num_variations_video
                            sample_stretched_v = pre_stretched_variations[frame_idx]
                            
                            sample_column = sample_stretched_v[:, x, :]
                            frame_out[:, x, :] = sample_column
                    else:
                        # Horizontaal mosaic dat rollend wordt gevormd
                        for y in range(height):
                            frame_idx = (y + frame_number) % num_variations_video
                            sample_stretched_h = pre_stretched_variations[frame_idx]
                            
                            sample_row = sample_stretched_h[y, :, :]
                            frame_out[y, :, :] = sample_row

                    process.stdin.write(frame_out.tobytes())

                    if frame_number % max(1, fps // 2) == 0:
                        progress.progress(min(1.0, (frame_number + 1) / total_frames))

                process.stdin.close()
                stderr = process.stderr.read()
                return_code = process.wait()

                if return_code != 0:
                    st.error("FFmpeg fout:\n\n" + stderr.decode("utf-8", errors="replace"))
                    raise RuntimeError("FFmpeg kon de video niet maken.")

            except Exception:
                try:
                    process.stdin.close()
                except:
                    pass
                process.kill()
                raise

            progress.progress(1.0)

            with open(output_path, "rb") as f:
                video_bytes = f.read()

            st.success("✅ Full HD Time Stretch video klaar!")
            st.video(video_bytes)
            st.download_button(
                label="⬇️ Download MP4 in maximale kwaliteit",
                data=video_bytes,
                file_name="time_stretch_moving_mosaic.mp4",
                mime="video/mp4"
            )

            try:
                os.remove(output_path)
            except:
                pass
