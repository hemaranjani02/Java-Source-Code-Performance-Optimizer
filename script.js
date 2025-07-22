'use strict';

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

// document.addEventListener("DOMContentLoaded", () => {
//   const input = document.getElementById("user-input");
//   input.addEventListener("input", () => {
//     console.log("User typing...");
//   });
// });

let selectedLanguage = 'java';

function setLanguage(lang) {
    selectedLanguage = lang;
    window.location.hash = lang;    // set the hash e.g. #java
    console.log(`Selected language: ${selectedLanguage}`);
    document.getElementById("user-input").placeholder = `Optimize your ${lang.toUpperCase()} code...`;

        // Show chat container and hide others
    document.querySelector('.chat-container').style.display = 'block';
    document.getElementById('summary-container').style.display = 'none';
    document.getElementById('summary-container1').style.display = 'none';

     // Clear previous messages and home content
    document.getElementById('chat-history').innerHTML = `
        <div class="message bot-message" style="background-color: white;">
           <h2><strong>${lang.toUpperCase()} Performance Optimization</strong></h2><br>
        </div>
    `;
 // Paste your ${lang.toUpperCase()} code below and click Send.
    // Optional: Clear input
    document.getElementById('user-input').value = '';
    document.getElementById("summary-error").textContent = "";
    document.getElementById("decompose-error").textContent = "";
    document.querySelector('.chat-input-container').style.display = 'flex';
}

function showSummaryUI() {
  document.querySelector('.chat-container').style.display = 'none';
  document.getElementById('summary-container').style.display = 'block';
  document.getElementById('summary-container1').style.display = 'none';
    // Clear previous validation message
  document.getElementById("summary-error").textContent = "";
}

function showDecomposeUI() {
  document.querySelector('.chat-container').style.display = 'none';
  document.getElementById('summary-container').style.display = 'none';  // hide summary
  document.getElementById('summary-container1').style.display = 'block';
  
  // Clear previous validation message
  document.getElementById("decompose-error").textContent = "";
}

function goHome() {
    document.getElementById('user-input').value = '';
    document.getElementById('user-input').placeholder = "Welcome to the Performance Code Optimizer...";
    document.getElementById('chat-history').innerHTML = `
        <div id="header" class="message bot-message" style="background-color: white;">
            <strong>Welcome to Performance Code Optimizer</strong><br>
            Select a language from the left to begin optimizing your code.
        </div>
    `;
    window.location.hash = '';  // clear hash when home

     // Reset views
    document.querySelector('.chat-container').style.display = 'block';
    document.getElementById('summary-container').style.display = 'none';
    document.getElementById('summary-container1').style.display = 'none';
        // ✅ Hide input area
    document.querySelector('.chat-input-container').style.display = 'none';
    document.getElementById("summary-error").textContent = "";
    document.getElementById("decompose-error").textContent = "";
}

function submitSummary() {
  const spinner = document.getElementById("summary-loading-spinner");
  const summaryBox = document.getElementById("summary-result");
  const errorBox = document.getElementById("summary-error");

  const data = {
    problem: document.getElementById("problem").value,
    impact: document.getElementById("impact").value,
    rootCause: document.getElementById("rootCause").value,
    fix: document.getElementById("fix").value,
  };
  
  // ✅ Validation block
    const missingFields = [];
    if (!data.problem) missingFields.push("Problem Statement");
    if (!data.impact) missingFields.push("Impact of Problem");
    if (!data.rootCause) missingFields.push("Root Cause");
    if (!data.fix) missingFields.push("Fix of Problem");

    if (missingFields.length > 0) {
    errorBox.textContent = `⚠️ Please fill in the following field(s): ${missingFields.join(", ")}.`;
    summaryBox.value = "";
    autoResizeTextarea(summaryBox);
    return;
    }

  errorBox.textContent = "";  // Clear previous error

  spinner.style.display = "block";
  summaryBox.value = "";
  autoResizeTextarea(summaryBox); // reset height

  axios.post("http://localhost:5000/summarize", data)
    .then((response) => {
      spinner.style.display = "none";
      summaryBox.value = response.data.summary;
      autoResizeTextarea(summaryBox); // resize to fit content
    })
    .catch((error) => {
      spinner.style.display = "none";
      errorBox.textContent = `Error: ${error.message}`;
      summaryBox.value = "";
      autoResizeTextarea(summaryBox);
    });
}


function decomposeSummary() {
  const summarizedInput = document.getElementById("summary-input").value.trim();
  const errorBox = document.getElementById("decompose-error");
  const spinner1 = document.getElementById("decompose-loading-spinner");

  // Clear previous error
  errorBox.textContent = '';

  // Show error if input is empty
  if (!summarizedInput) {
    errorBox.textContent = "⚠️ Please enter Summarized Output to decompose.";
    return;
  }

  // Show spinner
  spinner1.style.display = "block";

  // Clear previous outputs
  const decomposedProblem = document.getElementById("decomposed-problem");
  const decomposedImpact = document.getElementById("decomposed-impact");
  const decomposedRoot = document.getElementById("decomposed-root");
  const decomposedFix = document.getElementById("decomposed-fix");

  decomposedProblem.value = '';
  decomposedImpact.value = '';
  decomposedRoot.value = '';
  decomposedFix.value = '';

  autoResizeTextarea(decomposedProblem);
  autoResizeTextarea(decomposedImpact);
  autoResizeTextarea(decomposedRoot);
  autoResizeTextarea(decomposedFix);

  axios.post("http://localhost:5000/decompose-summary", {
    summary: summarizedInput
  })
  .then((response) => {
    spinner1.style.display = "none";
    const data = response.data;
    decomposedProblem.value = data.problem || '';
    decomposedImpact.value = data.impact || '';
    decomposedRoot.value = data.rootCause || '';
    decomposedFix.value = data.fix || '';

    autoResizeTextarea(decomposedProblem);
    autoResizeTextarea(decomposedImpact);
    autoResizeTextarea(decomposedRoot);
    autoResizeTextarea(decomposedFix);
  })
  .catch((error) => {
    spinner1.style.display = "none";
    errorBox.textContent = "❌ Failed to decompose: " + error.message;
  });
}

function disableSidebar(disable = true) {
  const links = document.querySelectorAll('.sidebar a');
  links.forEach(link => {
    if (disable) {
      link.classList.add('disabled-tab');
      link.style.pointerEvents = 'none';
      link.style.opacity = '0.5';
    } else {
      link.classList.remove('disabled-tab');
      link.style.pointerEvents = 'auto';
      link.style.opacity = '1';
    }
  });
}


function sendMessage() {
    const input = document.getElementById('user-input');
    const history = document.getElementById('chat-history');
    const spinner = document.getElementById('loading-spinner');
    const message = input.value.trim();

     // ✅ Disable tab switching while processing
    disableSidebar(true);

    if (message === '') {
    // Remove existing "No code provided" messages
    const existingErrors = history.querySelectorAll('.bot-message');
    existingErrors.forEach((msg) => {
        if (msg.textContent === "Error: No code provided") {
            msg.remove();
        }
    });

    // Show error only once
    const errMsg = document.createElement('div');
    errMsg.className = 'message bot-message';
    errMsg.style.color = 'red';
    errMsg.textContent = "Error: No code provided";
    history.appendChild(errMsg);
    history.scrollTop = history.scrollHeight;
    disableSidebar(false); // ✅ Re-enable sidebar on early exit
    return;
    }

    
    // Show spinner
    spinner.style.display = 'block';
    // Clear previous chat history
    // history.innerHTML = '';
    // while (history.firstChild) {
    //      history.removeChild(history.firstChild);
    // }
    // Clear All
    history.innerHTML = '';
    // 2. Re-add header
    const header = document.createElement('div');
    header.id = 'header';
    header.className = 'message bot-message';
    header.style.backgroundColor = 'white';
    header.innerHTML = `<h2><strong>${selectedLanguage.toUpperCase()} Performance Optimization</strong></h2>`;
    history.appendChild(header);

    const userMsg = document.createElement('div');
    userMsg.className = 'message user-message';
    userMsg.innerHTML = `
    <b>User Query</b>
    <pre><code>${escapeHTML(message)}</code></pre>
    `;

    const messageText = userMsg.textContent.trim();
    console.log(messageText);
    history.appendChild(userMsg);

     // API endpoint
    let apiUrl = '';
    if (selectedLanguage === 'java') {
        apiUrl = 'http://localhost:5000/optimize-java';
        console.log(apiUrl)
    } else if (selectedLanguage === 'python') {
        apiUrl = 'http://localhost:5000/optimize-python';
        console.log(apiUrl)
    } else if (selectedLanguage === 'js') {
        apiUrl = 'http://localhost:5000/optimize-js';
        console.log(apiUrl)
    } else {
        alert('Please select a language.');
        return;
    }

    // Call API
    axios.post(apiUrl, {
        code: message
    })
    // axios.post("http://localhost:5000/optimize", { code: messageText })
        .then(response => {
            spinner.style.display = 'none';  // Hide spinner
            disableSidebar(false);  // ✅ Re-enable after response
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
            spinner.style.display = 'none';
            disableSidebar(false); // ✅ Re-enable tab switching
            const errorMsg = document.createElement('div');
            errorMsg.className = 'message bot-message';
            errorMsg.style.color = 'red';

            if (error.response) {
                errorMsg.textContent = `Server Error: ${error.response.data.error || 'Something went wrong'}`;
            } else if (error.request) {
                errorMsg.textContent = "Error: Server is unreachable. Please try again later.";
            } else {
                errorMsg.textContent = `Unexpected Error: ${error.message}`;
            }

            history.appendChild(errorMsg);
            input.value = '';
            input.style.height = 'auto';
            history.scrollTop = history.scrollHeight;
        });
            // Reset the size of text area
    input.value = '';
    input.style.height = 'auto';  // Reset height
    history.scrollTop = history.scrollHeight;
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

function autoResizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = el.scrollHeight + 'px';
}

function initAutoResize() {
  const areas = document.querySelectorAll('.form-container textarea, .form-container1 textarea');
  areas.forEach(area => {
    autoResizeTextarea(area); // Resize once
    area.addEventListener('input', () => autoResizeTextarea(area));
  });
}

window.addEventListener('DOMContentLoaded', initAutoResize);

// window.onerror = function (message, source, lineno, colno, error) {
//   const errorDiv = document.createElement("div");
//   errorDiv.style.color = "red";
//   errorDiv.style.fontWeight = "bold";
//   errorDiv.style.padding = "100px";
//   errorDiv.style.backgroundColor = "#ffe6e6";
//   errorDiv.style.border = "1px solid red";
//   errorDiv.innerHTML = `
//     ⚠️ <strong>JavaScript Error:</strong><br>
//     ${message}<br>
//     at ${source}:${lineno}:${colno}
//   `;

//   document.body.prepend(errorDiv);
// };
