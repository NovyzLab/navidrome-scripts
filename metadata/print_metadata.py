import sys
import os
from pprint import pprint

try:
    from mutagen import File
except ImportError:
    print("Error: Mutagen library not found. Please install it with 'pip install mutagen' to run this script.")
    exit(1)

def print_metadata(file_path: str):
    """
    Prints all metadata tags for a given audio file.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at '{file_path}'")
        return
        
    print(f"--- Metadata for: {file_path} ---")
    try:
        audio = File(file_path)
        if audio is None:
            print("Could not read metadata. The file may be corrupted or an unsupported format.")
            return

        # Use pprint for a cleaner, more readable output of the dictionary
        pprint(audio.tags)
    except Exception as e:
        print(f"An error occurred while reading metadata: {e}")
    print("-" * (len(file_path) + 20))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python metadata_printer.py <path_to_audio_file>")
    else:
        file_path = sys.argv[1]
        print_metadata(file_path)
