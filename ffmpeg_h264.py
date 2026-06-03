import sys
import math

# ──────────────────────────────────────────────
# Standard resolutions, highest to lowest
# ──────────────────────────────────────────────
RESOLUTIONS = [
    (3840, 2160, "2160p (4K)"),
    (2560, 1440, "1440p (2K)"),
    (1920, 1080, "1080p (Full HD)"),
    (1280,  720, "720p  (HD)"),
    ( 854,  480, "480p  (SD)"),
    ( 640,  360, "360p"),
    ( 426,  240, "240p"),
]

BPP_GOOD       = 0.10
BPP_ACCEPTABLE = 0.05

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def parse_duration(s):
    parts = s.strip().split(":")
    if len(parts) != 3:
        raise ValueError
    h, m, sec = int(parts[0]), int(parts[1]), int(parts[2])
    return h * 3600 + m * 60 + sec

def format_duration(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def kib_to_kbps(kib, duration_seconds):
    return (kib * 8192) / duration_seconds / 1000

def round_to_nearest(value, step=32):
    return round(value / step) * step

def calculate_video_bitrate(target_mb, duration_seconds, audio_kbps):
    total_bits = target_mb * 1024 * 1024 * 8
    audio_bits = audio_kbps * 1000 * duration_seconds
    video_bits = total_bits - audio_bits
    if video_bits <= 0:
        raise ValueError("Audio alone exceeds the target file size!")
    return video_bits / duration_seconds / 1000

def get_input(prompt, validator=None, error_msg="Invalid input, try again."):
    while True:
        raw = input(prompt).strip()
        if validator:
            try:
                return validator(raw)
            except Exception:
                print(f"  ⚠  {error_msg}\n")
        else:
            return raw

def bpp(video_kbps, width, height, fps):
    return (video_kbps * 1000) / (width * height * fps)

def scale_to_fit(orig_w, orig_h, target_w, target_h):
    scale = min(target_w / orig_w, target_h / orig_h)
    w = math.floor(orig_w * scale / 2) * 2
    h = math.floor(orig_h * scale / 2) * 2
    return w, h

def analyse_resolution(video_kbps, orig_w, orig_h, fps):
    results = []
    for res_w, res_h, label in RESOLUTIONS:
        if res_w > orig_w or res_h > orig_h:
            continue
        sw, sh = scale_to_fit(orig_w, orig_h, res_w, res_h)
        b = bpp(video_kbps, sw, sh, fps)
        if b >= BPP_GOOD:
            quality = "✓ Good"
        elif b >= BPP_ACCEPTABLE:
            quality = "~ Acceptable"
        else:
            quality = "✗ Blurry"
        results.append({"label": label, "scaled": (sw, sh), "bpp": b, "quality": quality})
    return results

def recommend_resolution(analysis):
    for r in analysis:
        if r["bpp"] >= BPP_ACCEPTABLE:
            return r
    return analysis[-1]

def print_resolution_table(analysis, orig_w, orig_h, video_kbps, fps):
    source_bpp = bpp(video_kbps, orig_w, orig_h, fps)
    source_q = "✓ Good" if source_bpp >= BPP_GOOD else ("~ Acceptable" if source_bpp >= BPP_ACCEPTABLE else "✗ Blurry")

    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │              Resolution Quality Analysis                 │")
    print("  ├──────────────────┬────────────┬───────────┬─────────────┤")
    print("  │ Resolution       │ Scaled to  │ BPP       │ Quality     │")
    print("  ├──────────────────┼────────────┼───────────┼─────────────┤")
    print(f"  │ {'SOURCE (no scale)':<16} │ {orig_w}x{orig_h:<5} │ {source_bpp:<9.4f} │ {source_q:<11} │")
    print("  ├──────────────────┼────────────┼───────────┼─────────────┤")
    for r in analysis:
        sw, sh = r["scaled"]
        print(f"  │ {r['label']:<16} │ {sw}x{sh:<6} │ {r['bpp']:<9.4f} │ {r['quality']:<11} │")
    print("  └──────────────────┴────────────┴───────────┴─────────────┘")
    print(f"  BPP guide:  ≥ {BPP_GOOD} = Good   {BPP_ACCEPTABLE}–{BPP_GOOD} = Acceptable   < {BPP_ACCEPTABLE} = Blurry")

# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    print("=" * 60)
    print("    FFmpeg 2-Pass Encoding — Bitrate Calculator")
    print("=" * 60)
    print()

    # --- Input / output ---
    input_file  = get_input("Input file path  (e.g. input.mp4): ")
    output_file = get_input("Output file path (e.g. output.mp4): ")

    # --- Duration ---
    duration_seconds = get_input(
        "Video duration (HH:MM:SS): ",
        validator=parse_duration,
        error_msg="Use HH:MM:SS format, e.g. 02:35:00"
    )
    print(f"  → {format_duration(duration_seconds)} ({duration_seconds}s)")

    # --- Source resolution & FPS ---
    print()
    print("  To find resolution + framerate, run:")
    print(f'  ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate -of default=noprint_wrappers=1 "{input_file}"')
    print()
    orig_w = get_input(
        "  Source width  (e.g. 1920): ",
        validator=lambda x: int(x) if int(x) > 0 else 1/0,
        error_msg="Enter a positive integer."
    )
    orig_h = get_input(
        "  Source height (e.g. 1080): ",
        validator=lambda x: int(x) if int(x) > 0 else 1/0,
        error_msg="Enter a positive integer."
    )
    fps = get_input(
        "  Framerate (e.g. 24, 29.97, 60): ",
        validator=lambda x: float(x) if float(x) > 0 else 1/0,
        error_msg="Enter a positive number."
    )
    print(f"  → {orig_w}x{orig_h} @ {fps} fps")

    # --- Target size ---
    print()
    target_mb = get_input(
        "Target file size in MB: ",
        validator=lambda x: float(x) if float(x) > 0 else 1/0,
        error_msg="Enter a positive number, e.g. 700"
    )
    print(f"  → {target_mb} MB target")

    # --- Audio KiB ---
    print()
    print("  To find audio KiB, run:")
    print(f'  ffmpeg -i "{input_file}" -map 0:a:0 -c copy -f null -')
    print('  Look for "audio: XXXX KiB" in the output.')
    print()
    audio_kib = get_input(
        "  Enter audio KiB value: ",
        validator=lambda x: float(x) if float(x) > 0 else 1/0,
        error_msg="Enter a positive number, e.g. 142536"
    )

    # --- Calculations ---
    print()
    print("-" * 60)
    raw_audio_kbps = kib_to_kbps(audio_kib, duration_seconds)
    audio_kbps     = round_to_nearest(raw_audio_kbps, step=32)
    video_kbps     = calculate_video_bitrate(target_mb, duration_seconds, audio_kbps)
    video_kbps_int = round(video_kbps)
    est_mb = ((video_kbps_int + audio_kbps) * 1000 * duration_seconds) / (8 * 1024 * 1024)

    print(f"  Raw audio bitrate    : {raw_audio_kbps:.2f} kbps")
    print(f"  Rounded audio (-b:a) : {audio_kbps} kbps")
    print(f"  Video bitrate (-b:v) : {video_kbps_int} kbps")
    print(f"  Estimated output     : ~{est_mb:.1f} MB  (target: {target_mb} MB)")

    # --- Resolution / BPP analysis ---
    analysis       = analyse_resolution(video_kbps_int, orig_w, orig_h, fps)
    print_resolution_table(analysis, orig_w, orig_h, video_kbps_int, fps)

    recommendation = recommend_resolution(analysis)
    rec_w, rec_h   = recommendation["scaled"]
    source_bpp_val = bpp(video_kbps_int, orig_w, orig_h, fps)

    print()
    if source_bpp_val >= BPP_GOOD:
        print(f"  ► Bitrate is sufficient for {orig_w}x{orig_h}. No downscale needed.")
        use_scale = False
        enc_w, enc_h = orig_w, orig_h
    else:
        print(f"  ► Recommended resolution : {rec_w}x{rec_h}  ({recommendation['label']})")
        print(f"    BPP at this resolution : {recommendation['bpp']:.4f}  ({recommendation['quality']})")
        print(f"    BPP at source {orig_w}x{orig_h}  : {source_bpp_val:.4f}  — would look blurry")
        print()
        downscale = get_input(f"  Downscale to {rec_w}x{rec_h} for better quality? (y/n): ").lower()
        use_scale = downscale == "y"
        enc_w, enc_h = (rec_w, rec_h) if use_scale else (orig_w, orig_h)

    # --- Build & print commands ---
    scale_filter = f"scale={enc_w}:{enc_h}:flags=lanczos"

    if use_scale:
        pass1 = f'ffmpeg -y -i "{input_file}" -vf {scale_filter} -c:v libx264 -b:v {video_kbps_int}k -pass 1 -an -f null NUL'
        pass2 = f'ffmpeg -i "{input_file}" -vf {scale_filter} -c:v libx264 -b:v {video_kbps_int}k -pass 2 -c:a aac -b:a {audio_kbps}k "{output_file}"'
    else:
        pass1 = f'ffmpeg -y -i "{input_file}" -c:v libx264 -b:v {video_kbps_int}k -pass 1 -an -f null NUL'
        pass2 = f'ffmpeg -i "{input_file}" -c:v libx264 -b:v {video_kbps_int}k -pass 2 -c:a aac -b:a {audio_kbps}k "{output_file}"'

    print()
    print("=" * 60)
    print("  Your FFmpeg Commands")
    print("=" * 60)
    print()
    print("  :: Pass 1")
    print(f"  {pass1}")
    print()
    print("  :: Pass 2")
    print(f"  {pass2}")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
    input("\nPress Enter to exit...")