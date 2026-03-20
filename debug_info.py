import yt_dlp
ydl_opts = {'quiet': True}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info("https://soundcloud.com/beansclub/illneverfindthissoundofsilence", download=False)
    print("thumbnail key exists:", 'thumbnail' in info)
    print("thumbnails array exists:", 'thumbnails' in info)
    if 'thumbnails' in info:
        print("num thumbnails:", len(info['thumbnails']))
        print("latest:", info['thumbnails'][-1].get('url'))
