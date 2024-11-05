document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('scrapeForm');
    const progressContainer = document.querySelector('.progress-container');
    const progressBar = document.querySelector('.progress');
    const progressText = document.querySelector('.progress-text');
    const downloadSection = document.getElementById('downloadSection');
    const downloadBtn = document.getElementById('downloadBtn');
    const includeSentiment = document.getElementById('include_sentiment');
    const sentimentScoreOption = document.getElementById('sentiment_score_option');

    // Handle sentiment analysis checkbox
    includeSentiment.addEventListener('change', function() {
        sentimentScoreOption.style.display = this.checked ? 'block' : 'none';
        if (!this.checked) {
            document.getElementById('include_sentiment_score').checked = false;
        }
    });

    // Handle form submission
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Show progress and disable submit button
        progressContainer.style.display = 'block';
        downloadSection.style.display = 'none';
        const submitButton = form.querySelector('button[type="submit"]');
        submitButton.disabled = true;

        try {
            // Get form data
            const formData = new FormData(form);
            
            // Create query string
            const queryString = new URLSearchParams(formData).toString();
            
            // Start SSE connection
            const eventSource = new EventSource(`/scrape?${queryString}`);
            
            eventSource.onmessage = function(event) {
                const data = event.data;
                
                if (data === 'DONE') {
                    eventSource.close();
                    downloadSection.style.display = 'block';
                    submitButton.disabled = false;
                    progressText.textContent = 'Scraping complete!';
                } else if (data.startsWith('ERROR:')) {
                    eventSource.close();
                    submitButton.disabled = false;
                    progressContainer.style.display = 'none';
                    alert(data.substring(6));
                } else {
                    const progress = parseFloat(data);
                    progressBar.style.width = `${progress}%`;
                    progressText.textContent = `${Math.round(progress)}%`;
                }
            };

            eventSource.onerror = function(error) {
                eventSource.close();
                submitButton.disabled = false;
                progressContainer.style.display = 'none';
                alert('An error occurred while scraping. Please try again.');
            };

        } catch (error) {
            submitButton.disabled = false;
            progressContainer.style.display = 'none';
            alert('An error occurred. Please try again.');
        }
    });

    // Handle download button
    downloadBtn.addEventListener('click', async function() {
        const formData = new FormData(form);
        
        try {
            const response = await fetch('/download', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `reddit_posts_${new Date().toISOString().slice(0,10)}.csv`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
            } else {
                throw new Error('Download failed');
            }
        } catch (error) {
            alert('Error downloading file. Please try again.');
        }
    });
}); 