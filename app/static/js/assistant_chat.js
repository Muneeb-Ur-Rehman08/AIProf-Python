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
            messageDiv.className = `w-full text-right mb-4`;
            messageDiv.innerHTML = `
                <div class="inline-block bg-blue-600 rounded-lg p-3 text-white max-w-[80%]">
                    ${text}
                </div>
            `;
            document.getElementById('chat-container').appendChild(messageDiv);
        } else {
            let assistantMessageDiv = document.querySelector('.assistant-message-pending');
            if (!assistantMessageDiv) {
                assistantMessageDiv = document.createElement('div');
                assistantMessageDiv.className = `w-full text-left mb-4 assistant-message-pending`;
                assistantMessageDiv.innerHTML = `
                    <div class="inline-block bg-white/10 rounded-lg p-3 text-white max-w-[80%]">
                        ${text}
                    </div>
                `;
                document.getElementById('chat-container').appendChild(assistantMessageDiv);
            } else {
                const element = assistantMessageDiv.querySelector('div');
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

    {#function processMarkdownWithMermaid(divElement, textChunk) {#}
    {#    const existingMarkdown = divElement.getAttribute('data-raw') || '';#}
    {#    const updatedMarkdown = existingMarkdown + textChunk;#}
    {#    divElement.setAttribute('data-raw', updatedMarkdown);#}
    {##}
    {#    try {#}
    {#        const mermaidRegex = /```mermaid\n([\s\S]*?)```/g;#}
    {#        let mermaidIndex = 0;#}
    {#        const mermaidCharts = [];#}
    {##}
    {#        const processedMarkdown = updatedMarkdown.replace(mermaidRegex, (match, mermaidCode) => {#}
    {#            console.info(mermaidCode);#}
    {#            const placeholder = `<div class="mermaid" id="mermaid-chart-${mermaidIndex}">${mermaidCode}</div>`;#}
    {#            mermaidCharts.push({id: `mermaid-chart-${mermaidIndex}`, code: mermaidCode});#}
    {#            mermaidIndex++;#}
    {#            return placeholder;#}
    {#        });#}
    {##}
    {#        const parsedHTML = marked.parse(processedMarkdown);#}
    {#        divElement.innerHTML = parsedHTML;#}
    {#console.log(parsedHTML)#}
    {##}
    {#        setTimeout(() => {#}
    {#            mermaidCharts.forEach(chart => {#}
    {#                const chartElement = document.getElementById(chart.id);#}
    {#                if (chartElement) {#}
    {#                    try {#}
    {#                        console.warn("Rending chart with id ", chart.id);#}
    {#                        mermaid.render(chart.id, chart.code, (svgCode) => {#}
    {#                            console.log("SVG")#}
    {#                            console.log(svgCode);#}
    {#                            chartElement.innerHTML = svgCode;#}
    {#                        }, chartElement);#}
    {#                    } catch (err) {#}
    {#                        console.error(`Error rendering Mermaid chart for ID ${chart.id}:`, err);#}
    {#                    }#}
    {#                } else {#}
    {#                    console.error(`Chart element with ID ${chart.id} not found.`);#}
    {#                }#}
    {#            });#}
    {#        }, 2000);#}
    {##}
    {#    } catch (e) {#}
    {#        console.error('Error processing Markdown or rendering Mermaid diagrams:', e);#}
    {#    }#}
    {#}#}


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

        function sendPayload() {
            const promptInput = document.getElementById('prompt-input');
            const promptValue = promptInput.value.trim();

            if (!promptValue) return;

            // Append the user's message
            appendMessage(promptValue, true);
            // Append the loader message (assistant-message-pending)
            appendMessage(createLoadingAnimation(), false);

            promptInput.value = '';

            const payload = {
                conversation_id: '{{ assistant.id }}',
                message: promptValue,
                id: '{{ assistant.id }}'
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
                            // Streaming complete - remove the loader
                            const pendingMessage = document.querySelector('.assistant-message-pending');
                            if (pendingMessage) {
                                pendingMessage.classList.remove('assistant-message-pending');
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
