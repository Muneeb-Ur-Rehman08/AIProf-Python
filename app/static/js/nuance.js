let recognition = null;
let isListening = false;

// Initialize speech recognition
function initSpeechRecognition() {
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            document.getElementById('prompt-input').value = document.getElementById('prompt-input').value + ' ' + transcript;
        };

        recognition.onend = function() {
            isListening = false;
            updateMicButtonStyle();
        };

        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
            isListening = false;
            updateMicButtonStyle();
        };
    } else {
        console.error('Speech recognition not supported in this browser');
    }
}

// Toggle speech recognition
function toggleSpeechRecognition() {
    if (!recognition) {
        initSpeechRecognition();
    }

    if (isListening) {
        recognition.stop();
        isListening = false;
    } else {
        recognition.start();
        isListening = true;
        // Add auto-stop after 3 seconds
        setTimeout(() => {
            if (isListening) {
                recognition.stop();
                isListening = false;
                updateMicButtonStyle();
            }
        }, 3000);
    }
    updateMicButtonStyle();
}

// Update microphone button style based on listening state
function updateMicButtonStyle() {
    const micButton = document.getElementById('mic-button');
    if (isListening) {
        micButton.style.backgroundColor = 'var(--clr-main)';
    } else {
        micButton.style.backgroundColor = '';
    }
}

// Initialize speech recognition when the page loads
document.addEventListener('DOMContentLoaded', initSpeechRecognition);
