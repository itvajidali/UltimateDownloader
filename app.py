import threading
import uuid
import time
import os
import yt_dlp
from flask import Flask, render_template, request, jsonify, send_file, after_this_request

app = Flask(__name__)

# Global dictionary to store download jobs
# Structure: { job_id: { 'status': 'processing'|'finished'|'error', 'percent': 0, 'filename': None, 'error': None } }
download_jobs = {}

# Check for FFmpeg
def check_ffmpeg():
    from shutil import which
    if which('ffmpeg'):
        return True
    
    # Try to find it in likely locations (WinGet default)
    import glob
    user_home = os.path.expanduser("~")
    search_pattern = os.path.join(user_home, "AppData", "Local", "Microsoft", "WinGet", "Packages", "**", "ffmpeg.exe")
    candidates = glob.glob(search_pattern, recursive=True)
    
    if candidates:
        ffmpeg_path = candidates[0]
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        print(f"Found FFmpeg at: {ffmpeg_dir}")
        os.environ["PATH"] += os.pathsep + ffmpeg_dir
        return True
        
    return False

if not check_ffmpeg():
    print("CRITICAL WARNING: FFmpeg is not installed or not in PATH. MP3 conversion will fail!")

# Config
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'downloads')
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration_string'),
                'uploader': info.get('uploader')
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def download_thread(job_id, url, format_type='audio'):
    try:
        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    p = d.get('_percent_str', '0%').replace('%','')
                    download_jobs[job_id]['percent'] = float(p)
                except:
                    pass
            elif d['status'] == 'finished':
                download_jobs[job_id]['percent'] = 99 # Conversion starting

        # Base Options
        ydl_opts = {
            'quiet': True,
            'progress_hooks': [progress_hook],
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        }
        
        # Anti-Bot: Use cookies.txt if present
        if os.path.exists('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'
        else:
            # Fallback for local PC: Try to use browser cookies (Experimental)
            # This helps if running locally without a cookies file
            try:
                ydl_opts['cookiesfrombrowser'] = ('chrome',) 
            except:
                pass

        if format_type == 'video':
            # Video Options (Best Video + Best Audio -> MP4)
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
            })
        else:
            # Audio Options (Best Audio -> MP3)
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # For video, merge_output_format makes it .mp4
            # For audio, postprocessor makes it .mp3
            # We need to predict the final filename
            
            base, ext = os.path.splitext(filename)
            if format_type == 'video':
                final_file = base + ".mp4"
            else:
                final_file = base + ".mp3"
            
            # Update job
            download_jobs[job_id]['filename'] = os.path.basename(final_file)
            download_jobs[job_id]['status'] = 'finished'
            download_jobs[job_id]['percent'] = 100

    except Exception as e:
        download_jobs[job_id]['status'] = 'error'
        download_jobs[job_id]['error'] = str(e)


@app.route('/api/start_download', methods=['POST'])
def start_download():
    data = request.get_json()
    url = data.get('url')
    format_type = data.get('type', 'audio') # Default to audio
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
        
    if not check_ffmpeg():
             return jsonify({'error': 'FFmpeg is not installed on the server. Cannot convert to MP3/MP4.'}), 500

    job_id = str(uuid.uuid4())
    download_jobs[job_id] = {
        'status': 'processing',
        'percent': 0,
        'filename': None,
        'error': None
    }
    
    thread = threading.Thread(target=download_thread, args=(job_id, url, format_type))
    thread.start()
    
    return jsonify({'job_id': job_id})

@app.route('/api/progress/<job_id>')
def get_progress(job_id):
    job = download_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)

@app.route('/api/get_file/<filename>')
def get_file(filename):
    # Security check: ensure simple filename
    filename = os.path.basename(filename)
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    # host='0.0.0.0' makes it accessible to other devices on the network
    app.run(host='0.0.0.0', port=5000, debug=True)
