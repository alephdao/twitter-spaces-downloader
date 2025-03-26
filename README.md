# Twitter Spaces Downloader

A Python script to download Twitter Spaces info using yt-dlp. 

let's you
- download the video as .mp4 file
- converts the video to audio as .mp3 file
- option to transcribe the audio using gemini. 


## Prerequisites

- Python 3.x
- FFmpeg (required for audio conversion)

## Installation

1. Install FFmpeg:
   - macOS (using Homebrew): `brew install ffmpeg`
   - Linux: `sudo apt-get install ffmpeg`
   - Windows: Download from [FFmpeg website](https://ffmpeg.org/download.html)

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the script:
```bash
python download_space.py
```

The script will download the Twitter Space audio and save it as an MP3 file in the current directory. The file will be named `twitter_space_[timestamp].mp3`.

## Notes

- The script will automatically convert the downloaded audio to MP3 format
- The output filename includes a timestamp to avoid overwriting files
- If you encounter any errors, make sure you have FFmpeg installed and all dependencies are properly installed
