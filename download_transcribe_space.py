#!/usr/bin/env python3
import yt_dlp
import sys
import os
import argparse
from transcribe_audio import transcribe_audio, save_transcript

def download_twitter_space(keep_video=True, transcribe=True):
    url = "https://prod-fastly-us-west-2.video.pscp.tv/Transcoding/v1/hls/g6Syrfk5LarAkAKKs-tkYiEzlzxmAR5hrNg7LfKAd5aBMjJWUZneXxeBwNI2cMIw7tD-iHPWoY7bWGhoVhIU8Q/non_transcode/us-west-2/periscope-replay-direct-prod-us-west-2-public/master_dynamic_16703801036805117945.m3u8?type=replay"
    
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,es;q=0.8',
        'cache-control': 'no-cache',
        'origin': 'https://x.com',
        'pragma': 'no-cache',
        'referer': 'https://x.com/',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
    }
    
    # Base options for downloading
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'twitter_space_%(epoch)s.%(ext)s',
        'http_headers': headers,
    }
    
    # Add audio extraction only if we don't want to keep the video
    if not keep_video:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    
    try:
        # Download the file
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)
        
        # If we need to keep video but also transcribe, create MP3
        mp3_file = None
        if keep_video and transcribe:
            mp3_file = os.path.splitext(downloaded_file)[0] + '.mp3'
            if not os.path.exists(mp3_file):
                print("Converting video to MP3 for transcription...")
                audio_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.splitext(downloaded_file)[0] + '.%(ext)s',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                }
                with yt_dlp.YoutubeDL(audio_opts) as ydl:
                    ydl.download([url])
        
        # For transcription, use the MP3 file
        if transcribe:
            audio_path = mp3_file if mp3_file else downloaded_file
            if not audio_path.endswith('.mp3'):
                print("Error: Could not find or create MP3 file for transcription")
                return
            
            print(f"Transcribing audio from {audio_path}...")
            transcript = transcribe_audio(audio_path)
            transcript_path = os.path.splitext(audio_path)[0] + '.md'
            save_transcript(transcript, transcript_path)
            print(f"Transcription saved to {transcript_path}")
            
        return downloaded_file
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Download Twitter Space and optionally transcribe it')
    parser.add_argument('--no-video', action='store_true',
                      help='Do not keep the video file, extract audio only')
    parser.add_argument('--no-transcribe', action='store_true',
                      help='Do not transcribe the audio')
    
    args = parser.parse_args()
    
    keep_video = not args.no_video
    transcribe = not args.no_transcribe
    
    download_twitter_space(keep_video=keep_video, transcribe=transcribe)

if __name__ == "__main__":
    main() 
