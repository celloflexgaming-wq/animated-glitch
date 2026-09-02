import streamlit as st
import numpy as np
from PIL import Image
import subprocess
import tempfile
import os
import math
import io

st.set_page_config(
    page_title="Smooth Glitch Studio",
    layout="centered"
)

st.title("🎞️ Smooth Glitch Studio")

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

    # -----------------------------------------
    # MODUS SELECTIE
    # -----------------------------------------
    st.markdown("---")
    mode = st.radio(
        "Kies wat je wilt genereren:",
        ["🎥 Glitch Video (MP4)", "🖼️ Glitch Foto (Statisch)"],
        horizontal=True
    )
    st.markdown("---")

    # =========================================
    # MODUS 1: STATISCHE GLITCH FOTO
    # =========================================
    if mode == "🖼️ Glitch Foto (Statisch)":
        st.subheader("⚙️ Foto-instellingen (Standaard)")

        resolution_photo = st.selectbox(
            "Foto resolutie",
            [
                "1920 × 1080 — Full HD",
                "1280 × 720 — HD",
                "Originele beeldverhouding behouden"
            ],
            index=0
        )

        # Standaard ingesteld op 80 (reset altijd bij herladen)
        bands_count_photo = st.slider(
            "Aantal glitch-banden (bepaalt streepdikte)",
            20,
            200,
            80,
            key="photo_bands"
        )
        
        # Extra optie: Segment variatie voor foto
        segment_complexity_photo = st.slider(
            "Glitch complexiteit (Aantal splitsingen per streep)",
            1,
            8,
            3,
            key="photo_complexity"
        )

        if st.button(
            "🖼️ Genereer Glitch Foto",
            type="primary"
        ):
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

            rng = np.random.default_rng()
            band_edges = np.linspace(0, height, bands_count_photo + 1).astype(int)
            static_frame = np.zeros_like(img_array)

            for i in range(bands_count_photo):
                y_start = band_edges[i]
                y_end = band_edges[i + 1]
                band_height = y_end - y_start

                if band_height <= 0:
                    continue

                band_row = np.zeros((band_height, width, 3), dtype=np.uint8)
                num_segments = int(rng.integers(1, segment_complexity_photo + 1))

                if num_segments == 1:
                    splits = [0, width]
                else:
                    split_points = sorted(
                        rng.choice(
                            np.arange(1, width),
                            size=num_segments - 1,
                            replace=False
                        ).tolist()
                    )
                    splits = [0] + split_points + [width]

                for j in range(len(splits) - 1):
                    x_start = splits[j]
                    x_end = splits[j + 1]

                    if x_end <= x_start:
                        continue

                    sample_x = int(rng.integers(x_start, x_end))
                    source = img_array[y_start:y_end, sample_x:sample_x + 1, :]

                    band_row[:, x_start:x_end, :] = np.repeat(
                        source,
                        x_end - x_start,
                        axis=1
                    )

                static_frame[y_start:y_end, :, :] = band_row

            result_img = Image.fromarray(static_frame)
            st.image(result_img, caption="Gegenereerde Glitch Foto", use_container_width=True)

            buf = io.BytesIO()
            result_img.save(buf, format="PNG")
            st.download_button(
                label="⬇️ Download Glitch Foto (PNG)",
                data=buf.getvalue(),
                file_name="glitch_foto.png",
                mime="image/png"
            )

    # =========================================
    # MODUS 2: GLITCH VIDEO (MP4)
    # =========================================
    elif mode == "🎥 Glitch Video (MP4)":
        st.subheader("⚙️ Video-instellingen (Standaard)")

        # RESOLUTIE (Standaard Full HD -> index=0)
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

        # DUUR (Standaard 15 sec -> index=2)
        duration = st.selectbox(
            "Duur",
            [5, 10, 15],
            index=2
        )

        # FPS (Standaard 30 -> index=1)
        fps = st.selectbox(
            "FPS",
            [24, 30, 60],
            index=1
        )

        # KWALITEIT (Standaard Maximale kwaliteit -> index=0)
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

        # GLITCH BANDS / STREEPDIKTE (Standaard op 60)
        bands_count = st.slider(
            "Aantal horizontale glitch-banden (bepaalt streepdikte)",
            20,
            150,
            60
        )

        # EXTRA OPTIE: COMPLEXITEIT / BLOKKEN PER STREEP
        segment_complexity_video = st.slider(
            "Glitch complexiteit (Aantal segmenten per band)",
            1,
            6,
            3
        )

        # SNELHEID (Standaard op 3)
        speed = st.slider(
            "Animatiesnelheid",
            1,
            8,
            3
        )

        # START VIDEO RENDER
        if st.button(
            "🎬 Maak Full HD video",
            type="primary"
        ):

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

            img_array = np.array(
                img,
                dtype=np.uint8
            )

            height, width, channels = img_array.shape

            total_frames = int(duration * fps)

            st.write(f"**Resolutie:** {width} × {height}")
            st.write(f"**Frames:** {total_frames}")
            st.write(f"**Kwaliteit:** CRF {crf} / {preset}")

            rng = np.random.default_rng(42)

            band_edges = np.linspace(
                0,
                height,
                bands_count + 1
            ).astype(int)

            bands = []

            for i in range(bands_count):
                y_start = band_edges[i]
                y_end = band_edges[i + 1]

                band_height = y_end - y_start

                if band_height <= 0:
                    continue

                band_row = np.zeros(
                    (
                        band_height,
                        width,
                        3
                    ),
                    dtype=np.uint8
                )

                num_segments = int(
                    rng.integers(1, segment_complexity_video + 1)
                )

                if num_segments == 1:
                    splits = [0, width]
                else:
                    split_points = sorted(
                        rng.choice(
                            np.arange(1, width),
                            size=num_segments - 1,
                            replace=False
                        ).tolist()
                    )

                    splits = (
                        [0]
                        + split_points
                        + [width]
                    )

                for j in range(
                    len(splits) - 1
                ):
                    x_start = splits[j]
                    x_end = splits[j + 1]

                    if x_end <= x_start:
                        continue

                    sample_x = int(
                        rng.integers(
                            x_start,
                            x_end
                        )
                    )

                    source = img_array[
                        y_start:y_end,
                        sample_x:sample_x + 1,
                        :
                    ]

                    band_row[
                        :,
                        x_start:x_end,
                        :
                    ] = np.repeat(
                        source,
                        x_end - x_start,
                        axis=1
                    )

                direction = int(
                    rng.choice([-1, 1])
                )

                cycles = int(
                    rng.integers(
                        1,
                        speed + 1
                    )
                )

                phase = float(
                    rng.random()
                )

                bands.append(
                    {
                        "y_start": y_start,
                        "y_end": y_end,
                        "row": band_row,
                        "direction": direction,
                        "cycles": cycles,
                        "phase": phase
                    }
                )

            progress = st.progress(0)

            output_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".mp4"
            )

            output_path = output_file.name
            output_file.close()

            command = [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-f",
                "rawvideo",
                "-vcodec",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-s",
                f"{width}x{height}",
                "-r",
                str(fps),
                "-i",
                "-",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                preset,
                "-crf",
                str(crf),
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                output_path
            ]

            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            try:
                for frame_number in range(
                    total_frames
                ):
                    t = (
                        frame_number / fps
                    )

                    frame = np.zeros_like(
                        img_array
                    )

                    for band in bands:
                        y1 = band["y_start"]
                        y2 = band["y_end"]

                        band_row = band["row"]
                        direction = band["direction"]
                        cycles = band["cycles"]
                        phase = band["phase"]

                        movement = (
                            0.5
                            + 0.5
                            * math.sin(
                                2
                                * math.pi
                                * (
                                    cycles
                                    * t
                                    / duration
                                    + phase
                                )
                            )
                        )

                        shift = int(
                            (
                                movement - 0.5
                            )
                            * width
                            * direction
                        )

                        shifted = np.roll(
                            band_row,
                            shift,
                            axis=1
                        )

                        frame[
                            y1:y2,
                            :,
                            :
                        ] = shifted

                    process.stdin.write(
                        frame.tobytes()
                    )

                    if (
                        frame_number
                        % max(1, fps // 2)
                        == 0
                    ):
                        progress.progress(
                            min(
                                1.0,
                                (
                                    frame_number + 1
                                )
                                / total_frames
                            )
                        )

                process.stdin.close()

                stderr = (
                    process.stderr.read()
                )

                return_code = (
                    process.wait()
                )

                if return_code != 0:
                    st.error(
                        "FFmpeg fout:\n\n"
                        + stderr.decode(
                            "utf-8",
                            errors="replace"
                        )
                    )

                    raise RuntimeError(
                        "FFmpeg kon de video niet maken."
                    )

            except Exception:
                try:
                    process.stdin.close()
                except:
                    pass

                process.kill()

                raise

            progress.progress(1.0)

            with open(
                output_path,
                "rb"
            ) as f:
                video_bytes = f.read()

            st.success(
                "✅ Full HD video klaar!"
            )

            st.video(
                video_bytes
            )

            st.download_button(
                label="⬇️ Download MP4 in maximale kwaliteit",
                data=video_bytes,
                file_name="smooth_glitch_full_hd.mp4",
                mime="video/mp4"
            )

            try:
                os.remove(output_path)
            except:
                pass
