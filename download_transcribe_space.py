#!/usr/bin/env python3
import yt_dlp
import sys

def download_twitter_space():
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
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'twitter_space_%(epoch)s.%(ext)s',
        'http_headers': headers,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print(f"Error downloading: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    download_twitter_space() 
