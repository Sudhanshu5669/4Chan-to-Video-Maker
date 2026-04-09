import os
import PIL.Image

# ── Pillow 10 compatibility ──────────────────────────────────────────────────
if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = (
        PIL.Image.Resampling.LANCZOS
        if hasattr(PIL.Image, "Resampling")
        else PIL.Image.LANCZOS
    )

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    concatenate_audioclips,
)
from moviepy.video.fx.all import fadein, fadeout, loop as mpy_loop


FADE_DURATION = 0.25   # seconds for crossfade between cards
CARD_SCALE    = 0.82   # card width as fraction of background width


def make_video(
    bg_video_path: str,
    image_paths: list[str],
    audio_paths: list[str],
    output_path: str,
):
    """
    Assembles the final Short:
    - Background video loops for full duration
    - Each post card is centred on screen, synced to its TTS audio
    - Cards fade in/out with a short crossfade between them
    """
    if not image_paths:
        raise ValueError("No scenes to render.")

    # ── Load assets ──────────────────────────────────────────────────────────
    bg = VideoFileClip(bg_video_path)
    bg_w, bg_h = bg.size
    target_w = int(bg_w * CARD_SCALE)

    audio_clips = [AudioFileClip(p) for p in audio_paths]
    total_duration = sum(a.duration for a in audio_clips)

    # ── Loop / trim background ────────────────────────────────────────────────
    if bg.duration < total_duration:
        bg = mpy_loop(bg, duration=total_duration)
    else:
        bg = bg.subclip(0, total_duration)

    # ── Build image clips with correct start times ────────────────────────────
    card_clips = []
    t = 0.0

    for img_path, aud_clip in zip(image_paths, audio_clips):
        duration = aud_clip.duration

        card = (
            ImageClip(img_path)
            .resize(width=target_w)
            .set_duration(duration)
            .set_start(t)
            .set_position("center")
        )

        # Fade in at start, fade out at end (clamped so short clips don't break)
        fade = min(FADE_DURATION, duration / 3)
        card = fadein(card, fade)
        card = fadeout(card, fade)

        card_clips.append(card)
        t += duration

    # ── Composite: bg first, then all cards on top ────────────────────────────
    final = CompositeVideoClip([bg, *card_clips], size=(bg_w, bg_h))

    # ── Attach full audio track ───────────────────────────────────────────────
    master_audio = concatenate_audioclips(audio_clips)
    final = final.set_audio(master_audio)
    final = final.set_duration(total_duration)

    # ── Render ───────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    final.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="fast",          # faster encode; swap to "medium" for smaller file
        threads=4,
        logger=None,            # suppress moviepy's verbose frame log
    )

    # ── Cleanup ───────────────────────────────────────────────────────────────
    bg.close()
    for a in audio_clips:
        a.close()