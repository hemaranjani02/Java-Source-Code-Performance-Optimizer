window.onload = function () {
    const textarea = document.getElementById('user-input');

    textarea.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px'; 
    });
}

function sendMessage() {
    const input = document.getElementById('user-input');
    const history = document.getElementById('chat-history');
    const message = input.value.trim();

    if (message === '') return;

    // Clear previous chat history
    history.innerHTML = '';

    const userMsg = document.createElement('div');
    userMsg.className = 'message user-message';
    userMsg.innerHTML = `
    <b>User Query</b>
    <pre><code>${escapeHTML(message)}</code></pre>
    `;

    const messageText = userMsg.textContent.trim();
    console.log(messageText);
    history.appendChild(userMsg);

    axios.post("http://localhost:5000/optimize", { code: messageText })
        .then(response => {
            console.log("Optimized:", response.data.optimized);

            const botMsg = document.createElement('div');
            botMsg.className = 'message bot-message';

            const botreply = response.data.optimized;
            botMsg.innerHTML = formatLLMReply(botreply);

            setTimeout(() => history.appendChild(botMsg), 500);
            input.value = '';
            history.scrollTop = history.scrollHeight;
        })
        .catch(error => {
            console.error("Error:", error);
            const botMsg = document.createElement('div');
            botMsg.className = 'message bot-message';
            botMsg.textContent = String(error);
            setTimeout(() => history.appendChild(botMsg), 500);
            input.value = '';
            history.scrollTop = history.scrollHeight;
        });
}

function escapeHTML(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function formatLLMReply(reply) {
    reply = escapeHTML(reply);

    // Highlight code blocks
    reply = reply.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre style="background-color: rgb(70, 85, 70);"><code class="language-${lang || 'plaintext'}">${code}</code></pre>`;
    });

    // Line breaks for other text
    reply = reply.replace(/(?!<\/pre>)\n/g, '<br>');

    return reply;
}
