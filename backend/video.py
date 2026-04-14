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
    CompositeAudioClip,
    concatenate_audioclips,
)
from moviepy.video.fx.all import fadein, fadeout, loop as mpy_loop
from moviepy.audio.fx.all import audio_loop, audio_fadeout


FADE_DURATION = 0.25   # seconds for crossfade between cards
CARD_SCALE    = 0.82   # card width as fraction of background width


def make_video(
    bg_video_path: str,
    image_paths: list[str],
    audio_paths: list[str],
    output_path: str,
    music_path: str = None,
    music_volume: float = 0.15,
    fps: int = 30,
    preset: str = "fast",
    apply_ken_burns: bool = False,
):
    """
    Assembles the final Short:
    - Background video loops for full duration
    - Each post card is centred on screen, synced to its TTS audio
    - Cards fade in/out with a short crossfade between them
    - Optional Ken Burns zoom effect
    - Optional background music mixed at configurable volume
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

        if apply_ken_burns:
            # Subtle zoom from 1.0 to 1.1x over the duration
            def get_zoom_effect(dur):
                return lambda t: 1.0 + 0.1 * (t / dur)
            
            card = card.resize(get_zoom_effect(duration))


        # Fade in at start, fade out at end (clamped so short clips don't break)
        fade = min(FADE_DURATION, duration / 3)
        card = fadein(card, fade)
        card = fadeout(card, fade)

        card_clips.append(card)
        t += duration

    # ── Composite: bg first, then all cards on top ────────────────────────────
    final = CompositeVideoClip([bg, *card_clips], size=(bg_w, bg_h))

    # ── Build audio track ─────────────────────────────────────────────────────
    master_audio = concatenate_audioclips(audio_clips)

    # ── Mix in background music (if provided) ─────────────────────────────────
    if music_path and os.path.exists(music_path) and music_volume > 0:
        try:
            music = AudioFileClip(music_path)

            # Loop music if shorter than video, trim if longer
            if music.duration < total_duration:
                music = audio_loop(music, duration=total_duration)
            else:
                music = music.subclip(0, total_duration)

            # Fade out the last 2 seconds for a clean ending
            fade_dur = min(2.0, total_duration / 4)
            music = audio_fadeout(music, fade_dur)

            # Set volume (0.15 = subtle, 0.3 = noticeable, 0.5+ = prominent)
            music = music.volumex(music_volume)

            # Composite: TTS narration (full volume) + music (reduced volume)
            master_audio = CompositeAudioClip([master_audio, music])
        except Exception as e:
            print(f"  [Music] Warning: could not load music, skipping: {e}")

    final = final.set_audio(master_audio)
    final = final.set_duration(total_duration)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    final.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        preset=preset,
        threads=4,
        logger=None,            # suppress moviepy's verbose frame log
    )

    # ── Cleanup ───────────────────────────────────────────────────────────────
    bg.close()
    for a in audio_clips:
        a.close()