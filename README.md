# Twitter Space Downloader and Transcriber

This tool downloads Twitter Spaces as video and audio and optionally transcribes them using Google's Gemini AI API.

## Prerequisites

1. Python 3.x
2. Required Python packages:
   ```bash
   pip install yt-dlp pydub google-generativeai python-dotenv
   ```
3. FFmpeg (required for audio processing)
   - On macOS: `brew install ffmpeg`
   - On Ubuntu/Debian: `sudo apt-get install ffmpeg`
   - On Windows: Download from [FFmpeg website](https://ffmpeg.org/download.html)

4. Google AI API Key
   - Create a `.env` file in the project directory
   - Add your Google AI API key:
     ```
     GOOGLE_AI_API_KEY=your_api_key_here
     ```

## Usage

The script provides several options for downloading and processing Twitter Spaces:

1. Download video and create transcription (default):
```bash
python download_transcribe_space.py
```

2. Download video only (no transcription):
```bash
python download_transcribe_space.py --no-transcribe
```

3. Extract audio only (MP3) and create transcription:
```bash
python download_transcribe_space.py --no-video
```

4. Extract audio only (no transcription):
```bash
python download_transcribe_space.py --no-video --no-transcribe
```

## Output Files

The script generates files with consistent naming based on the download timestamp:
- Video file (if kept): `twitter_space_[timestamp].[ext]`
- MP3 file (if needed): `twitter_space_[timestamp].mp3`
- Transcription (if requested): `twitter_space_[timestamp].md`

## Features

- Downloads Twitter Spaces in highest available quality
- Option to keep or discard video file
- Automatic MP3 extraction when needed
- High-quality transcription using Google's Gemini AI
- Speaker detection and timestamps in transcriptions
- Progress indicators for each step

## Transcription Features

The transcription includes:
- Speaker identification (labeled as Speaker 1, Speaker 2, etc.)
- Timestamps throughout the conversation
- Proper formatting and paragraph breaks
- Markdown output for easy reading and sharing

## Error Handling

The script includes robust error handling for:
- Download failures
- Audio conversion issues
- Transcription errors
- File system operations

## Requirements

See `requirements.txt` for a complete list of Python dependencies.

## Testing 

python transcribe_audio.py gauntlet_demo_day_pt1.mp3 --test-duration 1200
