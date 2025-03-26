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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MAX_CHUNK_SIZE = 300 * 1024 * 1024  # 300MB limit for Gemini API
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

def get_file_chunks(audio_path):
    """
    Split audio file into chunks if it's too large
    Returns: List of temporary file paths for chunks
    """
    audio = AudioSegment.from_mp3(audio_path)
    total_duration = len(audio)
    
    # If file is small enough, return it as is
    if os.path.getsize(audio_path) <= MAX_CHUNK_SIZE:
        return [audio_path]
    
    # Calculate number of chunks needed
    num_chunks = math.ceil(total_duration / CHUNK_DURATION)
    chunk_paths = []
    
    logger.info(f"Splitting audio into {num_chunks} chunks...")
    
    # Create temporary directory for chunks
    with tempfile.TemporaryDirectory() as temp_dir:
        for i in range(num_chunks):
            start_time = i * CHUNK_DURATION
            end_time = min((i + 1) * CHUNK_DURATION, total_duration)
            
            chunk = audio[start_time:end_time]
            chunk_path = os.path.join(temp_dir, f"chunk_{i}.mp3")
            chunk.export(chunk_path, format="mp3")
            chunk_paths.append(chunk_path)
            
            logger.info(f"Created chunk {i+1}/{num_chunks}")
        
        # Return list of chunk paths
        return chunk_paths

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

def transcribe_audio(audio_path):
    """
    Transcribe audio file, handling large files by chunking
    """
    try:
        # Get chunks (might be just one if file is small enough)
        chunk_paths = get_file_chunks(audio_path)
        
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

def main():
    """
    Main function to handle MP3 transcription
    """
    if len(sys.argv) != 2:
        print("Usage: python transcribe.py <path_to_mp3_file>")
        sys.exit(1)

    mp3_path = sys.argv[1]
    
    if not os.path.exists(mp3_path):
        print(f"Error: File {mp3_path} does not exist")
        sys.exit(1)
        
    if not mp3_path.lower().endswith('.mp3'):
        print("Error: File must be an MP3 file")
        sys.exit(1)

    try:
        # Get output path by replacing .mp3 extension with .md
        output_path = os.path.splitext(mp3_path)[0] + '.md'
        
        print(f"Processing {mp3_path}...")
        transcript = transcribe_audio(mp3_path)
        save_transcript(transcript, output_path)
        print(f"Transcription complete! Output saved to {output_path}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
