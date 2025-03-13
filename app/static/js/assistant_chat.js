window.addEventListener('resize', () => {
    if (window.innerWidth >= 768) {
        document.getElementById('assistantChat').classList.remove('hidden');
        document.getElementById('assistantForm').classList.remove('hidden');

    } else {
        document.getElementById('assistantChat').classList.add('hidden');
    }
});

function appendMessage(text, assistant_id, isUser = false) {
    if (isUser) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `bg-purple-200 mb-4 rounded px-2.5 py-3 max-w-[60%] w-fit ml-auto text-black first-letter:uppercase first-letter:bold first-letter:text-xl`;
        messageDiv.innerHTML = `
            <div class="markdown-content prompt-content" id="prompt-content">${text}</div>
        `;
        document.getElementById('chat-container').appendChild(messageDiv);
    } else {
        let assistantMessageDiv = document.querySelector('.assistant-message-pending');
        if (!assistantMessageDiv) {
            assistantMessageDiv = document.createElement('div');
            assistantMessageDiv.className = `bg-[aliceblue] mb-4 rounded px-2.5 py-4 max-w-[90%] mr-auto text-black first-letter:uppercase first-letter:bold first-letter:text-md assistant-message-pending`;
            assistantMessageDiv.innerHTML = `
                <div class="markdown-content" id="prompt-response">
                    ${text}
                </div>
                <div class="button-group" style="display: none; align-items: center; gap: 5px;">
                    <button id='speak-button' onclick="toggleSpeech(this.parentElement.getAttribute('data-raw') || this.parentElement.textContent, this)" 
                            class=" transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 speak-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                  d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                        </svg>
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 stop-icon hidden" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                    <!-- Plus button -->
                    <button type="submit" class="transition-colors plus-button" hx-POST="/notes/c/${assistant_id}/" hx-trigger="click" hx-target="#notes-panel" hx-swap="afterbegin">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 plus-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
                        </svg>
                    </button>
                </div>
            `;
            document.getElementById('chat-container').appendChild(assistantMessageDiv);
        } else {
            const element = assistantMessageDiv.querySelector('.markdown-content');
            processMarkdownWithMermaid(element, text);
        }
        // Set the plus button's onclick to dynamically set htmx values
        document.querySelectorAll('.plus-button').forEach(function(button) {
            
                const messageContainer = button.closest('div.mb-4');


                // Find the previous user message (prompt)
                let currentElement = messageContainer;
                let promptContent = 'No prompt found';
                while (currentElement.previousElementSibling) {
                    currentElement = currentElement.previousElementSibling;
                    if (currentElement.querySelector('.prompt-content')) {
                        promptContent = currentElement.querySelector('.prompt-content').textContent;
                        break;
                    }
                }

                
                const responseMessage = messageContainer.querySelector('#prompt-response p')?.textContent || 'No response found';
        
        
                if (!responseMessage) {
                    console.error('No response message found in this container.');
                    return;
                }
        
                // Set HTMX attributes
                button.setAttribute('hx-vals', JSON.stringify({
                    'prompt': promptContent,
                    'response': responseMessage
                }));

                button.setAttribute('hx-indicator', '.header-progress')
        
                // Ensure HTMX processes the button and triggers the click
                htmx.process(button);
                
            
        });
          

        // Add the speech toggle logic for the speak button
        const speakButton = assistantMessageDiv.querySelector('#speak-button');
        speakButton.onclick = function() {
            toggleSpeech(this.parentElement.parentElement.getAttribute('data-raw') || 
                      this.parentElement.parentElement.textContent, 
                      this);
        };
    }

    const chatContainer = document.getElementById('chat-container');
    chatContainer.scrollTop = chatContainer.scrollHeight;
}


function processMarkdownWithMermaid(divElement, textChunk) {
    const existingMarkdown = divElement.getAttribute('data-raw') || '';
    const updatedMarkdown = existingMarkdown + textChunk;
    divElement.setAttribute('data-raw', updatedMarkdown);

    try {
        const mermaidRegex = /```mermaid\n([\s\S]*?)```/g;
        
        const processedMarkdown = updatedMarkdown.replace(mermaidRegex, (match, mermaidCode) => {
            console.info(`Found Mermaid code:\n${mermaidCode}`);
            const safeCode = stripMarkdown(mermaidCode);
            console.log('SafeCode')
            console.log(safeCode);
            return `<div class="mermaid">${safeCode}</div>`;
        });
        
        const parsedHTML = marked.parse(processedMarkdown);
        divElement.innerHTML = parsedHTML;
        
        // Add speak button if this is the final chunk (no pending class)
        
        setTimeout(() => {
            try {
                console.warn("Initializing Mermaid.js for rendering");
                mermaid.initialize({startOnLoad: false});
                mermaid.init(undefined, divElement.querySelectorAll('.mermaid'));
                console.info("Mermaid diagrams rendered successfully.");
            } catch (err) {
                console.error("Error rendering Mermaid diagrams:", err);
            }
        }, 200);

    } catch (e) {
        console.error('Error processing Markdown or Mermaid diagrams:', e);
    }
}

function stripMarkdown(markdownText) {
    // Parse Markdown into HTML
    const html = marked.parse(markdownText);

    // Use a temporary DOM element to strip HTML tags
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;

    // Return plain text content
    const filtered_text = tempDiv.textContent || tempDiv.innerText || '';
    return filtered_text
        // Remove code blocks
        .replace(/```[\s\S]*?```/g, '')
        // Remove inline code
        .replace(/`([^`]+)`/g, '$1')
        // Remove headers
        .replace(/^#+\s+/gm, '')
        // Remove emphasis (*, **, _, __)
        .replace(/(\*|_){1,2}([^*_]+)\1{1,2}/g, '$2')
        // Remove links
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
        // Remove images
        .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
        // Remove blockquotes
        .replace(/^\s*>+\s?/gm, '')
        // Remove unordered list markers
        .replace(/^\s*[-+*]\s+/gm, '')
        // Remove ordered list markers
        .replace(/^\s*\d+\.\s+/gm, '')
        // Remove horizontal rules
        .replace(/^-{3,}$/gm, '')
        // Remove any remaining HTML tags
        .replace(/<\/?[^>]+(>|$)/g, '')
        // Replace multiple newlines with a single newline
        .replace(/\n{2,}/g, '\n')
        .trim();
}


    // default message
    // appendMessage('Hello! How can I assist you today?', true);
    // // default response
    // appendMessage('I am an AI assistant designed to help you with your questions and tasks. How can I assist you today?', false);

    function createLoadingAnimation() {
        return `
        <div class="loading-dots flex space-x-2">
            <div class="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style="animation-delay: -0.3s;"></div>
            <div class="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style="animation-delay: -0.15s;"></div>
            <div class="w-2 h-2 bg-blue-600 rounded-full animate-bounce"></div>
        </div>
    `;
    }

    async function sendPayload(assistant_id) {
    const promptInput = document.getElementById('prompt-input');
    const promptValue = promptInput.value.trim();

    if (!promptValue) return;

    // Append the user's message
    appendMessage(promptValue, assistant_id, true);
    // Append the loader message (assistant-message-pending)
    appendMessage(createLoadingAnimation(), assistant_id, false);

    promptInput.value = '';

    const payload = {
        message: promptValue,
        id: assistant_id
    };

    try {
        const response = await fetch('/chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'HX-Request': 'true'
            },
            body: JSON.stringify(payload)
        });

        const reader = response.body.getReader();
        let buffer = '';
        const decoder = new TextDecoder();

        // Read the stream progressively
        const processStream = async ({ done, value }) => {
            if (done) {
                // Streaming complete - remove the loader and show speak/plus buttons
                const pendingMessage = document.querySelector('.assistant-message-pending');
                if (pendingMessage) {
                    pendingMessage.classList.remove('assistant-message-pending');
                    // Show buttons (speak/plus)
                    const buttonGroup = pendingMessage.querySelector('.button-group');
                    if (buttonGroup) {
                        buttonGroup.style.display = 'inline-flex'; // Show the buttons
                    }
                }
                return;
            }

            // Decode the current chunk
            buffer += decoder.decode(value, { stream: true });

            // Extract valid JSON objects from the buffer
            const messages = buffer.split('\n').filter(line => line.trim() !== '');

            messages.forEach(message => {
                try {
                    const parsedChunk = JSON.parse(message);

                    // Process each parsed JSON chunk
                    appendMessage(parsedChunk.text, assistant_id, false);

                    // Handle the last chunk (e.g., show buttons)
                    if (parsedChunk.isLastChunk) {
                        let assistantMessageDiv = document.querySelector('.assistant-message-pending');
                        if (assistantMessageDiv) {
                            const buttonGroup = assistantMessageDiv.querySelector('.button-group');
                            if (buttonGroup) {
                                buttonGroup.style.display = 'inline-flex'; // Show the buttons
                            }
                        }
                        if (parsedChunk.showReview) {
                            openReviewModal();
                        }
                    }
                } catch (e) {
                    console.error('Error parsing JSON chunk:', e);
                }
            });

            // Continue reading the stream
            reader.read().then(processStream);
        };

        // Start processing the stream
        reader.read().then(processStream);

    } catch (error) {
        console.error('Error:', error);
        // On error, remove the loader and show error message
        const pendingMessage = document.querySelector('.assistant-message-pending');
        if (pendingMessage) {
            pendingMessage.remove();
        }
        appendMessage('Error: Failed to get response', assistant_id, false);
    }
}

    
    

    function toggleSpeech(text, buttonElement) {
        if (window.speechSynthesis.speaking) {
            stopSpeech();
            updateSpeakButtons(false);
        } else {
            speak(text);
            updateSpeakButtons(true);
            
            // Add event listener for when speech ends
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.onend = () => {
                updateSpeakButtons(false);
            };
            window.speechSynthesis.speak(utterance);
        }
    }

    function updateSpeakButtons(isSpeaking) {
        document.querySelectorAll('.speak-icon, .stop-icon').forEach(icon => {
            icon.classList.toggle('hidden', icon.classList.contains('speak-icon') ? isSpeaking : !isSpeaking);
        });
    }

    function openReviewModal() {
        document.getElementById("review-modal").classList.remove("hidden");
    }

    function closeReviewModal() {
        document.getElementById("review-modal").classList.add("hidden");
    }

    // Function to show toast message
    function showToast(message, isSuccess = true) {
        const toast = document.createElement("div");
        toast.classList.add("fixed", "bottom-4", "right-4", "px-4", "py-2", "rounded-lg", "shadow-lg");
        toast.classList.add(isSuccess ? "bg-green-500" : "bg-red-500", "text-white");
        toast.innerText = message;

        document.body.appendChild(toast);

        // Remove the toast after 3 seconds
        setTimeout(() => {
        toast.remove();
        }, 3000);
    }

    // Close modal when clicking outside
    document.getElementById("review-modal").addEventListener("click", function(e) {
        if (e.target === this) {
        closeReviewModal();
        }
    });

    // Handle escape key
    document.addEventListener("keydown", function(e) {
        if (e.key === "Escape") {
        closeReviewModal();
        }
    });


    // Function to open modal
    function openQuizModal() {
        var modal = document.getElementById('quiz-modal');
        if (modal) {
            modal.classList.remove('hidden');
        }
    }

    // Function to close modal
    function closeQuizModal() {
        var modal = document.getElementById('quiz-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }

    