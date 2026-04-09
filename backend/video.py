import PIL.Image
# --- MONKEY PATCH FOR PILLOW 10 COMPATIBILITY ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS if hasattr(PIL.Image, "Resampling") else PIL.Image.LANCZOS

from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips, concatenate_audioclips

def make_video(bg_video_path, image_paths, audio_paths, output_path):
    
    # Load background video first so we can get its dimensions
    bg_clip = VideoFileClip(bg_video_path)
    bg_width, bg_height = bg_clip.size
    
    # Calculate perfect width for the screenshot (85% of screen width)
    target_width = int(bg_width * 0.85)
    
    audio_clips = []
    image_clips = []
    
    for img_path, aud_path in zip(image_paths, audio_paths):
        aud = AudioFileClip(aud_path)
        audio_clips.append(aud)
        
        # Load image, sync to audio, AND resize to prevent overflow
        img = ImageClip(img_path).set_duration(aud.duration)
        img = img.resize(width=target_width)
        img = img.set_position("center")
        
        image_clips.append(img)
        
    final_audio = concatenate_audioclips(audio_clips)
    final_images = concatenate_videoclips(image_clips).set_position("center")
    
    # Loop or cut background video
    if bg_clip.duration < final_audio.duration:
        from moviepy.video.fx.all import loop
        bg_clip = loop(bg_clip, duration=final_audio.duration)
    else:
        bg_clip = bg_clip.subclip(0, final_audio.duration)
        
    final_video = CompositeVideoClip([bg_clip, final_images])
    final_video = final_video.set_audio(final_audio)
    
    final_video.write_videofile(
        output_path, 
        fps=30, 
        codec="libx264", 
        audio_codec="aac",
        threads=4
    )