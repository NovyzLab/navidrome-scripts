import yt_dlp
import os
import glob

ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': '/tmp/thumb_test/Beansclub - Ill Never Find.%(ext)s',
    'writethumbnail': True,
    'quiet': False,
    'postprocessors': [
        {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'opus',
            'preferredquality': '0',
        }
    ],
}

os.makedirs('/tmp/thumb_test', exist_ok=True)
for f in glob.glob('/tmp/thumb_test/*'):
    os.remove(f)

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.extract_info("https://soundcloud.com/beansclub/illneverfindthissoundofsilence", download=True)

print("Files in directory:")
for f in glob.glob('/tmp/thumb_test/*'):
    print(f)
