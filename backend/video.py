import numpy as np
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip

def make_video(bg_video_path, image_path, audio_path, output_path):
    # Load audio
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration
    
    # Load and crop background video to match audio length
    bg_clip = VideoFileClip(bg_video_path)
    if bg_clip.duration < duration:
        print("Warning: Background video is shorter than the TTS audio!")
    bg_clip = bg_clip.subclip(0, duration)
    
    # Load image overlay
    img_clip = ImageClip(image_path).set_duration(duration)
    
    # Add an alpha channel (mask) to the image for transparency
    img_clip = img_clip.add_mask()
    
    # --- The Reveal Animation Logic ---
    def reveal_mask(get_frame, t):
        # Get the original mask frame (usually an array of 1.0s or 255s)
        mask_frame = get_frame(t)
        h = mask_frame.shape[0]
        
        # Calculate how much should be visible based on current time
        progress = min(1.0, t / duration)
        visible_h = int(h * progress)
        
        # Create a copy and make the bottom portion transparent (0)
        new_mask = np.copy(mask_frame)
        if visible_h < h:
            new_mask[visible_h:, :] = 0 
            
        return new_mask
        
    # Apply the animated mask to the image
    img_clip.mask = img_clip.mask.fl(reveal_mask)
    
    # Center the image on the screen
    img_clip = img_clip.set_position("center")
    
    # Composite them together
    final_video = CompositeVideoClip([bg_clip, img_clip])
    final_video = final_video.set_audio(audio_clip)
    
    # Render (optimized for TikTok/Shorts viewing)
    final_video.write_videofile(
        output_path, 
        fps=30, 
        codec="libx264", 
        audio_codec="aac",
        threads=4
    )