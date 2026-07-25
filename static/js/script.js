// Interview Logic
function nextPhase(currentId, nextId) {
    document.getElementById(`phase-${currentId}`).style.display = 'none';
    document.getElementById(`phase-${nextId}`).style.display = 'block';
}

function prevPhase(currentId, prevId) {
    document.getElementById(`phase-${currentId}`).style.display = 'none';
    document.getElementById(`phase-${prevId}`).style.display = 'block';
}

async function loadFollowups() {
    const form = document.getElementById('interview-form');
    const formData = new FormData(form);
    const symptoms = formData.getAll('symptoms');

    if (symptoms.length === 0) {
        alert("Please select at least one symptom to proceed (or if none, we will skip detailed questions).");
        // For demo, allowing progression even if empty, but maybe should just skip to submit?
        // Let's just proceed.
    }

    try {
        const response = await fetch('/api/get_followups', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symptoms: symptoms })
        });
        const data = await response.json();

        const container = document.getElementById('followup-questions-container');
        container.innerHTML = '';

        if (data.followups.length === 0) {
            container.innerHTML = '<p>No specific follow-up questions needed.</p>';
        } else {
            data.followups.forEach(q => {
                let html = `<div class="form-group"><label>${q.text}</label>`;
                if (q.type === 'scale' || q.type === 'choice') {
                    html += `<select name="${q.id}">`;
                    q.options.forEach(opt => {
                        html += `<option value="${opt}">${opt}</option>`;
                    });
                    html += `</select>`;
                }
                html += `</div>`;
                container.innerHTML += html;
            });
        }

        nextPhase('symptoms', 'followups');

    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred loading questions.');
    }
}

async function submitInterview() {
    const form = document.getElementById('interview-form');
    const formData = new FormData(form); // This might not capture dynamically added fields if not re-queried?
    // FormData captures all fields in the form element at moment of construction.

    // We need to manually construct the JSON because FormData.entries() on a form with same-named checkboxes needs handling
    const data = {};
    data.answers = {};
    data.symptoms = formData.getAll('symptoms');

    for (let [key, value] of formData.entries()) {
        if (key !== 'symptoms') {
            data.answers[key] = value;
        }
    }

    try {
        const response = await fetch('/api/interview_submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const res = await response.json();
        if (res.status === 'success') {
            window.location.href = res.redirect;
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

// Chatbot Logic
let chatHistory = [];

function handleEnter(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
}

function useChip(text) {
    const input = document.getElementById('chat-input');
    input.value = text;
    sendMessage();
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    // Hide starter chips
    const chips = document.getElementById('starter-chips');
    if (chips) chips.style.display = 'none';

    // Add user message
    addMessageToChat(message, 'user');
    chatHistory.push({ role: 'user', content: message });
    input.value = '';

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, history: chatHistory })
        });
        const data = await response.json();

        // Add bot response
        addMessageToChat(data.response, 'bot');
        chatHistory.push({ role: 'assistant', content: data.response });

    } catch (error) {
        console.error('Error:', error);
        addMessageToChat("Sorry, I'm having trouble connecting.", 'bot');
    }
}

function addMessageToChat(text, sender) {
    const div = document.createElement('div');
    div.className = `message ${sender}`;

    if (sender === 'bot') {
        // Wrap bot content in a container for expand/collapse
        const contentDiv = document.createElement('div');
        contentDiv.className = 'msg-content';
        if (typeof marked !== 'undefined') {
            contentDiv.innerHTML = marked.parse(text);
        } else {
            contentDiv.innerText = text;
        }

        // Remove extra margins from paragraphs
        contentDiv.querySelectorAll('p').forEach(p => p.style.margin = '0 0 8px 0');
        const lastP = contentDiv.querySelector('p:last-child');
        if (lastP) lastP.style.margin = '0';

        div.appendChild(contentDiv);

        // Create toggle button
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'msg-toggle';
        toggleBtn.textContent = 'Show more ▼';
        div.appendChild(toggleBtn);

        // After rendering, check if content overflows 200px
        requestAnimationFrame(() => {
            if (contentDiv.scrollHeight > 220) {
                contentDiv.classList.add('collapsed');
                toggleBtn.classList.add('visible');
                toggleBtn.addEventListener('click', function() {
                    const isCollapsed = contentDiv.classList.contains('collapsed');
                    if (isCollapsed) {
                        contentDiv.classList.remove('collapsed');
                        contentDiv.classList.add('expanded');
                        toggleBtn.textContent = 'Show less ▲';
                    } else {
                        contentDiv.classList.remove('expanded');
                        contentDiv.classList.add('collapsed');
                        toggleBtn.textContent = 'Show more ▼';
                    }
                });
            }
        });
    } else {
        // User message — render directly
        if (typeof marked !== 'undefined') {
            div.innerHTML = marked.parse(text);
        } else {
            div.innerText = text;
        }
        div.querySelectorAll('p').forEach(p => p.style.margin = '0');
    }

    const chatWindow = document.getElementById('chat-window');
    chatWindow.appendChild(div);

    // Reliable auto-scroll: wait for DOM to paint, then scroll
    requestAnimationFrame(() => {
        setTimeout(() => {
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }, 50);
    });
}

async function finishChat() {
    if (chatHistory.length === 0) {
        alert("Please have a conversation first.");
        return;
    }

    try {
        const response = await fetch('/api/chat_analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ history: chatHistory })
        });
        const res = await response.json();
        if (res.status === 'success') {
            window.location.href = res.redirect;
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Analysis failed.');
    }
}
