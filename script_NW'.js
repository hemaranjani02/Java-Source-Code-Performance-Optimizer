window.onload = function () {
  const textarea = document.getElementById('user-input');
  textarea.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
  });

  const lang = window.location.hash.replace("#", "");
  if (["java", "python", "js"].includes(lang)) {
    setLanguage(lang);
  } else {
    goHome();
  }
}

let selectedLanguage = 'java';

function setLanguage(lang) {
  selectedLanguage = lang;
  window.location.hash = lang;
  document.getElementById("user-input").placeholder = `Optimize your ${lang.toUpperCase()} code...`;
  document.getElementById('chat-history').innerHTML = `
    <div class="message bot-message" style="background-color: white;">
      <h2><strong>${lang.toUpperCase()} Performance Optimization</strong></h2>
    </div>`;
  document.getElementById('user-input').value = '';
  document.querySelector('.chat-container').style.display = 'block';
  document.getElementById('summary-container').style.display = 'none';
  document.getElementById('decomposer-container').style.display = 'none';
}

function goHome() {
  document.getElementById('user-input').value = '';
  document.getElementById('user-input').placeholder = "Welcome to the Performance Code Optimizer...";
  document.getElementById('chat-history').innerHTML = `
    <div class="message bot-message" style="background-color: white;">
      <strong>Welcome to Performance Code Optimizer</strong><br>
      Select a language from the left to begin optimizing your code.
    </div>`;
  window.location.hash = '';
  document.querySelector('.chat-container').style.display = 'block';
  document.getElementById('summary-container').style.display = 'none';
  document.getElementById('decomposer-container').style.display = 'none';
}

function showSummaryUI() {
  document.querySelector('.chat-container').style.display = 'none';
  document.getElementById('summary-container').style.display = 'block';
  document.getElementById('decomposer-container').style.display = 'none';
}

function showDecomposerUI() {
  document.querySelector('.chat-container').style.display = 'none';
  document.getElementById('summary-container').style.display = 'none';
  document.getElementById('decomposer-container').style.display = 'block';
}

function submitSummary() {
  const spinner = document.getElementById("summary-loading-spinner");
  const summaryBox = document.getElementById("summary-result");

  const data = {
    problem: document.getElementById("problem").value,
    impact: document.getElementById("impact").value,
    rootCause: document.getElementById("rootCause").value,
    fix: document.getElementById("fix").value,
  };

  spinner.style.display = "block";
  summaryBox.value = "";

  axios.post("http://localhost:5000/summarize", data)
    .then((response) => {
      spinner.style.display = "none";
      summaryBox.value = response.data.summary;
    })
    .catch((error) => {
      spinner.style.display = "none";
      summaryBox.value = `Error: ${error.message}`;
    });
}

function decomposeSummary() {
  const spinner = document.getElementById("summary-loading-spinner");
  const summary = document.getElementById("summary-input").value;
    if (!summary || summary.trim() === "") {
    alert("Please enter a summary before decomposing.");
    return;
    }
  spinner.style.display = "block";

  axios.post("http://localhost:5000/decompose", { summary })
    .then((response) => {
      spinner.style.display = "none";
      document.getElementById("problem").value = response.data.problem || "";
      document.getElementById("impact").value = response.data.impact || "";
      document.getElementById("rootCause").value = response.data.rootCause || "";
      document.getElementById("fix").value = response.data.fix || "";
    })
    .catch((error) => {
      spinner.style.display = "none";
      alert("Error: " + error.message);
    });
}

function sendMessage() {
  const input = document.getElementById('user-input');
  const history = document.getElementById('chat-history');
  const spinner = document.getElementById('loading-spinner');
  const message = input.value.trim();

  if (message === '') return;

  spinner.style.display = 'block';
  history.innerHTML = '';

  const header = document.createElement('div');
  header.className = 'message bot-message';
  header.style.backgroundColor = 'white';
  header.innerHTML = `<h2><strong>${selectedLanguage.toUpperCase()} Performance Optimization</strong></h2>`;
  history.appendChild(header);

  const userMsg = document.createElement('div');
  userMsg.className = 'message user-message';
  userMsg.innerHTML = `<b>User Query</b><pre><code>${escapeHTML(message)}</code></pre>`;
  history.appendChild(userMsg);

  let apiUrl = '';
  if (selectedLanguage === 'java') apiUrl = 'http://localhost:5000/optimize-java';
  else if (selectedLanguage === 'python') apiUrl = 'http://localhost:5000/optimize-python';
  else if (selectedLanguage === 'js') apiUrl = 'http://localhost:5000/optimize-js';
  else return alert('Please select a language.');

  axios.post(apiUrl, { code: message })
    .then(response => {
      spinner.style.display = 'none';
      const botMsg = document.createElement('div');
      botMsg.className = 'message bot-message';
      botMsg.innerHTML = formatLLMReply(response.data.optimized);
      setTimeout(() => history.appendChild(botMsg), 500);
      input.value = '';
      input.style.height = 'auto';
      history.scrollTop = history.scrollHeight;
    })
    .catch(error => {
      spinner.style.display = 'none';
      const botMsg = document.createElement('div');
      botMsg.className = 'message bot-message';
      botMsg.textContent = String(error);
      setTimeout(() => history.appendChild(botMsg), 500);
    });
}

function escapeHTML(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function formatLLMReply(reply) {
  reply = escapeHTML(reply);
  reply = reply.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) =>
    `<pre style="background-color: rgb(70, 85, 70);"><code class="language-${lang || 'plaintext'}">${code}</code></pre>`);
  reply = reply.replace(/(?!<\/pre>)\n/g, '<br>');
  return reply;
}
