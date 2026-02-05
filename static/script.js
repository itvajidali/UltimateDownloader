document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('urlInput');
    const getInfoBtn = document.getElementById('getInfoBtn');
    const resultArea = document.getElementById('resultArea');
    const loading = document.getElementById('loading');
    const downloadBtn = document.getElementById('downloadBtn');

    // Elements to populate
    const thumbnail = document.getElementById('thumbnail');
    const videoTitle = document.getElementById('videoTitle');
    const uploader = document.getElementById('uploader');
    const duration = document.getElementById('duration');
    const message = document.getElementById('message');

    let currentUrl = '';

    const showMessage = (msg, type = 'info') => {
        message.textContent = msg;
        message.className = type === 'error' ? 'error-msg' : 'success-msg';
        message.classList.remove('hidden');
        setTimeout(() => message.classList.add('hidden'), 5000);
    };

    const fetchInfo = async () => {
        const url = urlInput.value.trim();
        if (!url) {
            showMessage('Please enter a valid URL', 'error');
            return;
        }

        // Reset UI
        resultArea.classList.add('hidden');
        loading.classList.remove('hidden');

        try {
            const response = await fetch('/api/info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to fetch info');
            }

            // Populate Info
            currentUrl = url;
            thumbnail.src = data.thumbnail;
            videoTitle.textContent = data.title;
            uploader.textContent = data.uploader;
            duration.textContent = data.duration;

            loading.classList.add('hidden');
            resultArea.classList.remove('hidden');

        } catch (error) {
            loading.classList.add('hidden');
            showMessage(error.message, 'error');
        }
    };

    const downloadVideo = async () => {
        if (!currentUrl) return;

        const format = document.getElementById('formatSelect').value;
        const btnText = format === 'audio' ? 'Download MP3' : 'Download MP4';

        downloadBtn.textContent = 'Starting...';
        downloadBtn.disabled = true;

        // Switch to loading view
        resultArea.classList.add('hidden');
        loading.classList.remove('hidden');
        document.getElementById('loadingText').textContent = 'Initializing Download...';
        const progressContainer = document.getElementById('progress-container');
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');

        progressContainer.classList.remove('hidden');
        progressFill.style.width = '0%';
        progressText.textContent = '0%';

        try {
            // Step 1: Start Job
            const startResponse = await fetch('/api/start_download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: currentUrl,
                    type: format
                })
            });

            if (!startResponse.ok) {
                const err = await startResponse.json();
                throw new Error(err.error || 'Failed to start download');
            }

            const { job_id } = await startResponse.json();

            // Step 2: Poll Progress
            const poll = setInterval(async () => {
                try {
                    const statusResponse = await fetch(`/api/progress/${job_id}`);
                    const statusData = await statusResponse.json();

                    if (statusData.status === 'processing' || statusData.status === 'downloading') {
                        const percent = statusData.percent || 0;
                        progressFill.style.width = `${percent}%`;
                        progressText.textContent = `${percent.toFixed(1)}%`;

                        if (percent >= 99) {
                            document.getElementById('loadingText').textContent = 'Converting to MP3... (This may take a moment)';
                            progressFill.style.boxShadow = '0 0 15px #fff'; // Add glow effect
                        } else {
                            document.getElementById('loadingText').textContent = 'Downloading...';
                        }
                    }
                    else if (statusData.status === 'finished') {
                        clearInterval(poll);
                        progressFill.style.width = '100%';
                        progressText.textContent = 'Conversion Complete!';
                        document.getElementById('loadingText').textContent = 'Finalizing...';

                        // Trigger file download
                        window.location.href = `/api/get_file/${statusData.filename}`;

                        // Reset UI after short delay
                        setTimeout(() => {
                            loading.classList.add('hidden');
                            resultArea.classList.remove('hidden');

                            const format = document.getElementById('formatSelect').value;
                            downloadBtn.textContent = format === 'audio' ? 'Download MP3' : 'Download MP4';

                            downloadBtn.disabled = false;
                            showMessage('Download Complete!', 'success');
                        }, 2000);
                    }
                    else if (statusData.status === 'error') {
                        clearInterval(poll);
                        throw new Error(statusData.error);
                    }
                } catch (e) {
                    clearInterval(poll);
                    handleError(e);
                }
            }, 1000);

        } catch (error) {
            handleError(error);
        }
    };

    const handleError = (error) => {
        loading.classList.add('hidden');
        resultArea.classList.remove('hidden');
        downloadBtn.textContent = 'Download MP3';
        downloadBtn.disabled = false;
        showMessage(error.message, 'error');
    };

    const updateButtonText = () => {
        const format = document.getElementById('formatSelect').value;
        downloadBtn.textContent = format === 'audio' ? 'Download MP3' : 'Download MP4';
    };

    document.getElementById('formatSelect').addEventListener('change', updateButtonText);

    getInfoBtn.addEventListener('click', () => {
        fetchInfo().then(updateButtonText);
    });

    downloadBtn.addEventListener('click', downloadVideo);

    urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            fetchInfo().then(updateButtonText);
        }
    });
});
