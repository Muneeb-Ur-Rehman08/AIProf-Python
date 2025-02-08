    window.addEventListener('resize', () => {
        if (window.innerWidth >= 768) {
            document.getElementById('assistantChat').classList.remove('hidden');
            document.getElementById('assistantForm').classList.remove('hidden');

        } else {
            document.getElementById('assistantChat').classList.add('hidden');
        }
    });

    function appendMessage(text, isUser = false) {
        if (isUser) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `bg-purple-200 mb-4 rounded px-2.5 py-3 max-w-[60%] w-fit ml-auto text-black first-letter:uppercase first-letter:bold first-letter:text-xl`;
            messageDiv.innerHTML = `
                <div class="markdown-content">
                    ${text}
                </div>
            `;
            document.getElementById('chat-container').appendChild(messageDiv);
        } else {
            let assistantMessageDiv = document.querySelector('.assistant-message-pending');
            if (!assistantMessageDiv) {
                assistantMessageDiv = document.createElement('div');
                assistantMessageDiv.className = `bg-[aliceblue] mb-4 rounded px-2.5 py-4 max-w-[90%] mr-auto text-black first-letter:uppercase first-letter:bold first-letter:text-md assistant-message-pending`;
                assistantMessageDiv.innerHTML = `
                    <div class="markdown-content">
                        ${text}
                    </div>
                `;
                document.getElementById('chat-container').appendChild(assistantMessageDiv);
            } else {
                const element = assistantMessageDiv.querySelector('.markdown-content');
                processMarkdownWithMermaid(element, text);
            }
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
            if (!divElement.parentElement.classList.contains('assistant-message-pending')) {
                const speakButton = `
                    <button onclick="toggleSpeech(this.parentElement.getAttribute('data-raw') || this.parentElement.textContent, this)" 
                            class=" transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 speak-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                  d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                        </svg>
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 stop-icon hidden" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                `;
                divElement.insertAdjacentHTML('beforeend', speakButton);
            }
            
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
            <div class="flex space-x-2">
                <div class="w-1 h-2 rounded-full animate-bounce" style="animation-delay: -0.3s; background: var(--clr-main); transform: translateY(-50px);"></div>
                <div class="w-1 h-2 rounded-full animate-bounce" style="animation-delay: -0.15s; background: var(--clr-main); transform: translateY(-50px);"></div>
                <div class="w-1 h-2 rounded-full animate-bounce" style="background: var(--clr-main); transform: translateY(-50px);"></div>
            </div>
        `;
        }

        function sendPayload(assistant_id) {
            const promptInput = document.getElementById('prompt-input');
            const promptValue = promptInput.value.trim();

            if (!promptValue) return;

            // Append the user's message
            appendMessage(promptValue, true);
            // Append the loader message (assistant-message-pending)
            appendMessage(createLoadingAnimation(), false);

            promptInput.value = '';

            const payload = {
                message: promptValue,
                id: assistant_id
            };

            fetch('/assistantchat/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'HX-Request': 'true'
                },
                body: JSON.stringify(payload)
            })
                .then(response => {
                    const reader = response.body.getReader();

                    function processStream({done, value}) {
                        if (done) {
                            // Streaming complete - remove the loader and add speak button
                            const pendingMessage = document.querySelector('.assistant-message-pending');
                            if (pendingMessage) {
                                pendingMessage.classList.remove('assistant-message-pending');
                                const messageDiv = pendingMessage.querySelector('div');
                                const speakButton = `
                                    <button onclick="toggleSpeech(this.parentElement.getAttribute('data-raw') || this.parentElement.textContent, this)" 
                                            class=" transition-colors">
                                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 speak-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                                  d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                                        </svg>
                                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 stop-icon hidden" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                                  d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z M6 18L18 6M6 6l12 12" />
                                        </svg>
                                    </button>
                                `;
                                messageDiv.insertAdjacentHTML('beforeend', speakButton);
                            }
                            return;
                        }

                        const chunk = new TextDecoder().decode(value);
                        appendMessage(chunk, false);
                        return reader.read().then(processStream);
                    }

                    return reader.read().then(processStream);
                })
                .catch(error => {
                    console.error('Error:', error);
                    // On error, remove the loader and show error message
                    const pendingMessage = document.querySelector('.assistant-message-pending');
                    if (pendingMessage) {
                        pendingMessage.remove();
                    }
                    appendMessage('Error: Failed to get response', false);
                });
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
