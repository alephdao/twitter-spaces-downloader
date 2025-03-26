import os
import google.generativeai as genai
import logging
from dotenv import load_dotenv
import base64
import gc
from contextlib import contextmanager
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import sys
from pydub import AudioSegment
import tempfile
import math
import argparse
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_CHUNK_SIZE = 50 * 1024 * 1024  # 50MB default limit for Gemini API
CHUNK_DURATION = 10 * 60 * 1000  # 10 minutes in milliseconds

# Load environment variables
load_dotenv()
GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY")

if not GOOGLE_AI_API_KEY:
    raise ValueError("Missing GOOGLE_AI_API_KEY in .env file")

# Initialize Gemini
genai.configure(api_key=GOOGLE_AI_API_KEY)

# Add a context manager for model handling
@contextmanager
def model_context():
    """
    Context manager to handle model initialization and cleanup with safety settings
    """
    try:
        model = genai.GenerativeModel('models/gemini-2.0-flash-exp', 
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            }
        )
        yield model
    finally:
        # Cleanup
        del model
        gc.collect()

# Update the prompt to be more specific
TRANSCRIPTION_PROMPT = """Transcribe this audio accurately in its original language.

If there are multiple speakers, identify and label them as 'Speaker 1:', 'Speaker 2:', etc. Include timestamps.

Do not include any headers, titles, or additional text - only the transcription itself.

When transcribing, add line breaks between different paragraphs or distinct segments of speech to improve readability.

"""

def trim_audio_with_ffmpeg(input_path, output_path, duration):
    """
    Trim audio file using ffmpeg without loading entire file into memory
    """
    try:
        cmd = ['ffmpeg', '-i', input_path, '-t', str(duration), '-acodec', 'copy', output_path, '-y']
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr.decode()}")
        return False

class AudioChunker:
    def __init__(self, max_chunk_size=DEFAULT_CHUNK_SIZE, test_duration=None):
        self.max_chunk_size = max_chunk_size
        self.test_duration = test_duration  # in seconds
        self.temp_dir = None
        self.chunk_paths = []

    def __enter__(self):
        self.temp_dir = tempfile.mkdtemp()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clean up temporary files
        if self.temp_dir:
            for chunk_path in self.chunk_paths:
                try:
                    if os.path.exists(chunk_path):
                        os.remove(chunk_path)
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file {chunk_path}: {e}")
            try:
                os.rmdir(self.temp_dir)
            except Exception as e:
                logger.warning(f"Failed to remove temporary directory {self.temp_dir}: {e}")

    def get_file_chunks(self, audio_path):
        """
        Split audio file into chunks if it's too large
        Returns: List of temporary file paths for chunks
        """
        # For test mode, trim the audio first using ffmpeg
        if self.test_duration is not None:
            trimmed_path = os.path.join(self.temp_dir, "trimmed.mp3")
            if trim_audio_with_ffmpeg(audio_path, trimmed_path, self.test_duration):
                logger.info(f"Created trimmed audio file for test duration: {self.test_duration}s")
                audio_path = trimmed_path
                self.chunk_paths.append(trimmed_path)
            else:
                logger.warning("Failed to trim audio, proceeding with full file")
        
        # If file is small enough, use it directly
        if os.path.getsize(audio_path) <= self.max_chunk_size:
            if audio_path not in self.chunk_paths:
                self.chunk_paths.append(audio_path)
            return self.chunk_paths
        
        # For larger files, split into chunks
        audio = AudioSegment.from_mp3(audio_path)
        total_duration = len(audio)
        
        # Calculate number of chunks needed
        num_chunks = math.ceil(total_duration / CHUNK_DURATION)
        logger.info(f"Splitting audio into {num_chunks} chunks...")
        
        for i in range(num_chunks):
            start_time = i * CHUNK_DURATION
            end_time = min((i + 1) * CHUNK_DURATION, total_duration)
            
            chunk = audio[start_time:end_time]
            chunk_path = os.path.join(self.temp_dir, f"chunk_{i}.mp3")
            chunk.export(chunk_path, format="mp3")
            self.chunk_paths.append(chunk_path)
            
            logger.info(f"Created chunk {i+1}/{num_chunks}")
        
        return self.chunk_paths

def transcribe_audio_chunk(audio_path):
    """
    Transcribe a single audio chunk using Gemini API
    """
    try:
        # Read the audio file
        with open(audio_path, 'rb') as audio_file:
            audio_data = audio_file.read()
            
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        content_parts = [
            {"text": TRANSCRIPTION_PROMPT},
            {
                "inline_data": {
                    "mime_type": "audio/mp3",
                    "data": audio_base64
                }
            }
        ]
        
        with model_context() as current_model:
            response = current_model.generate_content(content_parts)
            transcript = response.text
            
            # Remove any variations of transcription headers
            transcript = transcript.replace("# Transcription\n\n", "")
            transcript = transcript.replace("Okay, here is the transcription:\n", "")
            transcript = transcript.replace("Here's the transcription:\n", "")
            transcript = transcript.strip()
            
            # Count actual speaker labels using a more precise pattern
            speaker_labels = set()
            for line in transcript.split('\n'):
                if line.strip().startswith(('Speaker ', '**Speaker ')):
                    for i in range(1, 10):
                        if f"Speaker {i}:" in line or f"**Speaker {i}:**" in line:
                            speaker_labels.add(i)
            
            # Log number of speakers detected
            logger.info(f"Number of unique speakers detected: {len(speaker_labels)}")
            logger.info(f"Speaker numbers found: {sorted(list(speaker_labels))}")
            
            return transcript
            
    except Exception as e:
        logger.error(f"Error transcribing audio chunk: {str(e)}")
        raise
    finally:
        gc.collect()

def transcribe_audio(audio_path, max_chunk_size=DEFAULT_CHUNK_SIZE, test_duration=None):
    """
    Transcribe audio file, handling large files by chunking
    """
    try:
        with AudioChunker(max_chunk_size=max_chunk_size, test_duration=test_duration) as chunker:
            # Get chunks (might be just one if file is small enough)
            chunk_paths = chunker.get_file_chunks(audio_path)
            
            if len(chunk_paths) == 1:
                # Single chunk, process normally
                return transcribe_audio_chunk(chunk_paths[0])
            else:
                # Multiple chunks, process each and combine
                logger.info(f"Processing {len(chunk_paths)} chunks...")
                transcripts = []
                
                for i, chunk_path in enumerate(chunk_paths):
                    logger.info(f"Processing chunk {i+1}/{len(chunk_paths)}...")
                    chunk_transcript = transcribe_audio_chunk(chunk_path)
                    transcripts.append(f"\n\n--- Segment {i+1} ---\n\n{chunk_transcript}")
                
                # Combine all transcripts
                return "".join(transcripts)
                
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        raise

def save_transcript(transcript, output_path):
    """
    Save transcript to a markdown file
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(transcript)
        logger.info(f"Transcript saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving transcript: {str(e)}")
        raise

def parse_size(size_str):
    """Convert a string like '10mb' to bytes"""
    size_str = size_str.lower()
    if size_str.endswith('mb'):
        return int(float(size_str[:-2]) * 1024 * 1024)
    elif size_str.endswith('gb'):
        return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
    elif size_str.endswith('kb'):
        return int(float(size_str[:-2]) * 1024)
    else:
        try:
            return int(size_str)
        except ValueError:
            raise argparse.ArgumentTypeError('Size must be specified as a number with optional suffix kb/mb/gb')

def main():
    """
    Main function to handle MP3 transcription
    """
    parser = argparse.ArgumentParser(description='Transcribe MP3 audio files using Gemini API')
    parser.add_argument('mp3_path', help='Path to the MP3 file to transcribe')
    parser.add_argument('--chunk-size', type=parse_size, default=DEFAULT_CHUNK_SIZE,
                      help='Maximum chunk size (e.g., "10mb", "1gb"). Default is 50mb')
    parser.add_argument('--test-duration', type=int,
                      help='Test mode: Only process the first N seconds of audio')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.mp3_path):
        print(f"Error: File {args.mp3_path} does not exist")
        sys.exit(1)
        
    if not args.mp3_path.lower().endswith('.mp3'):
        print("Error: File must be an MP3 file")
        sys.exit(1)

    try:
        # Get output path by replacing .mp3 extension with .md
        output_path = os.path.splitext(args.mp3_path)[0] + '.md'
        
        print(f"Processing {args.mp3_path}...")
        print(f"Using maximum chunk size of {args.chunk_size / (1024*1024):.2f}MB")
        if args.test_duration:
            print(f"Test mode: Processing only first {args.test_duration} seconds")
        
        transcript = transcribe_audio(args.mp3_path, max_chunk_size=args.chunk_size, 
                                   test_duration=args.test_duration)
        save_transcript(transcript, output_path)
        print(f"Transcription complete! Output saved to {output_path}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
