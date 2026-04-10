import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload

# The permissions we need to upload videos
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def authenticate_youtube():
    """Handles the OAuth login and saves the token for future autonomous runs."""
    credentials = None
    
    # If we already logged in before, load the saved token
    if os.path.exists("token.json"):
        credentials = Credentials.from_authorized_user_file("token.json", SCOPES)
        
    # If we don't have a token, or it expired, log in via browser
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            from google.auth.transport.requests import Request
            credentials.refresh(Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                "client_secrets.json", SCOPES
            )
            credentials = flow.run_local_server(port=0)
            
        # Save the token for the next time the script runs
        with open("token.json", "w") as token_file:
            token_file.write(credentials.to_json())
            
    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

def upload_to_youtube(video_path, title, description, tags, category_id="24", privacy="private", progress_callback=None):
    """
    Uploads a video to YouTube.
    Category 24 = Entertainment, 20 = Gaming, 22 = Blogs
    Privacy can be 'public', 'private', or 'unlisted'.
    """
    youtube = authenticate_youtube()

    print(f"\n[YouTube API] Preparing to upload: {title}")

    # Build the metadata payload
    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id
        },
        "status": {
            "privacyStatus": privacy, 
            "selfDeclaredMadeForKids": False
        }
    }

    # Attach the physical video file
    media_file = MediaFileUpload(video_path, chunksize=-1, resumable=True)

    # Create the API request
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media_file
    )

    # Execute the upload
    response = None
    try:
        print("[YouTube API] Uploading video... (this may take a few minutes)")
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress_pct = int(status.progress() * 100)
                print(f"Uploaded {progress_pct}%.")
                if progress_callback:
                    progress_callback(status.progress())
                    
        print(f"\n✅ SUCCESS! Video uploaded to YouTube.")
        print(f"🔗 Link: https://youtu.be/{response['id']}")
        return response['id']
    except googleapiclient.errors.HttpError as e:
        print(f"\n❌ An HTTP error occurred: {e}")
        return None