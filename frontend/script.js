const API_URL = window.location.origin;


function switchScreen(screenId) {
    document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
    document.getElementById(screenId).classList.remove('hidden');
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function switchTab(tab) {
    const isSignup = tab === 'signup';
    document.getElementById('login-form').classList.toggle('hidden', isSignup);
    document.getElementById('signup-form').classList.toggle('hidden', !isSignup);
}

async function showTab(tabId) { 
    document.getElementById('tab-assistant').classList.toggle('hidden', tabId !== 'assistant');
    document.getElementById('tab-results').classList.toggle('hidden', tabId !== 'results');

    const navA = document.getElementById('nav-assistant');
    const navR = document.getElementById('nav-results');
    if (tabId === 'assistant') {
        navA.classList.add('active');
        navR.classList.remove('active');
    } else {
        navR.classList.add('active');
        navA.classList.remove('active');
        await loadRecommendations();
    }
}
async function loadRecommendations() {
    const sessionId = localStorage.getItem('session_id');
    if (!sessionId) return;

    const grid = document.getElementById('results-grid');
    grid.innerHTML = '<p class="text-center muted">Chargement...</p>';

    try {
        const res  = await fetch(`${API_URL}/recommendations/${sessionId}`);
        const data = await res.json();
        displayResults(data.recommendations);
    } catch (e) {
        grid.innerHTML = '<p class="text-center muted">Erreur de chargement.</p>';
    }
}


async function handleAuth(event) {
    event.preventDefault();
    const isSignup = !document.getElementById('signup-form').classList.contains('hidden');

    const email    = document.getElementById(isSignup ? 'signup-email'    : 'login-email').value;
    const password = document.getElementById(isSignup ? 'signup-password' : 'login-password').value;

    const url  = isSignup ? '/signup' : '/login';
    const body = isSignup
        ? { email, password, full_name: document.getElementById('signup-name').value }
        : { email, password };

    try {
        const res  = await fetch(`${API_URL}${url}`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(body)
        });

        const data = await res.json();
        if (!res.ok) { alert(data.detail); return; }

        // signup — switch to login form
        if (isSignup) { switchTab('login'); return; }

        // login — save session and enter chat
        localStorage.setItem('session_id', data.session_id);
        document.getElementById('username').innerText = data.user || email.split('@')[0];
        switchScreen('chat');
        sendMessage('__start__');

    } catch (e) {
        alert('Erreur serveur, réessaie.');
    }
}


let hasStarted = false;

async function sendMessage(msg = "") {
    const sessionId = localStorage.getItem('session_id');
    if (!sessionId) return;

    if (msg && msg.trim() !== "__start__") {
        addMessage(msg, "user");
    }

    if (!hasStarted && (!msg || msg.trim() === "")) {
        msg = "__start__";
        hasStarted = true;
    } else {
        hasStarted = true;
    }

    const typing = addMessage("...", "bot");

    try {
        const res = await fetch(`${API_URL}/chat`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ message: msg, session_id: sessionId })
        });

        const data = await res.json();
        typing.remove();

        addMessage(data.reply || "Erreur", 'bot');

        if (data.profile) updateProgress(data.profile);
        if (data.status === "completed") displayResults(data.recommended_schools);

    } catch (e) {
        typing.remove();
        addMessage("Erreur serveur", 'bot');
    }
}

function addMessage(text, sender) {
    const box = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = `${sender === 'user' ? 'user-msg' : 'bot-msg'} p-4 animate-in`;

    const urlRegex = /(https?:\/\/[^\s]+|www\.[^\s]+)/g;
    let html = text.replace(urlRegex, url => {
        const href = url.startsWith('http') ? url : `https://${url}`;
        return `<a href="${href}" target="_blank" class="link underline font-bold">${url}</a>`;
    });

    html = html.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
    div.innerHTML = html.replace(/\n/g, '<br>');
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
    return div;
}

function updateProgress(profile) {
    const fields = ['bac', 'moyenne', 'objectif'];
    const filled = fields.filter(f => {
        const val = profile[f];
        return Array.isArray(val) ? val.length > 0 : val !== null && val !== undefined;
    }).length;

    const pct = Math.round((filled / fields.length) * 100);
    document.getElementById('progress-bar').style.width = pct + '%';
    document.getElementById('progress-pct').innerText   = pct + '%';
}

function displayResults(schools) {
    const grid = document.getElementById('results-grid');
    grid.innerHTML = '';

    if (!schools || schools.length === 0) {
        grid.innerHTML = '<p class="text-center muted">Complete ton profil dans le chat dabord.</p>';
        return;
    }

    schools.forEach((school, index) => {
        const badge = school.eligible
            ? '<span class="badge badge-green">Eligible</span>'
            : '<span class="badge badge-amber">Seuil limite</span>';

        
        const pct = Math.min(Math.round((school.score / 80) * 100), 100);
        const scoreColor = pct >= 70 ? '#7C3AED' : pct >= 40 ? '#D97706' : '#DC2626';

        const filieres = school.filieres
            ? school.filieres.split(',').slice(0, 3).map(f =>
                `<span class="tag">${f.trim()}</span>`).join('')
            : '';

        const card = document.createElement('div');
        card.className = 'school-card animate-in';
        if (index === 0) card.classList.add('top-card');

        card.innerHTML = `
            <div class="card-top">
                <div style="display:flex; align-items:center; gap:8px;">
                    <h3 style="margin:0;">${school.name}</h3>
                    ${index === 0 ? '<span class="badge badge-purple">Recommande</span>' : badge}
                </div>
                <div style="font-size:20px; font-weight:500; color:${scoreColor};">
                    ${pct}%
                </div>
            </div>
            <p class="muted" style="margin:4px 0 8px;">${school.full_name}</p>
            <div style="margin-bottom:8px;">${filieres}</div>
            <div class="seuil-box">
                <span style="font-size:12px; color:var(--color-text-secondary);">
                    ${school.eligible 
                        ? '✓ Eligible · seuil ' + school.seuil 
                        : '⚠ Seuil requis : ' + school.seuil}
                </span>
                <span style="font-size:12px; color:var(--color-text-secondary);">
                    📍 ${school.villes || 'Maroc'}
                </span>
            </div>
        `;
        grid.appendChild(card);
    });
}


document.addEventListener("DOMContentLoaded", () => {
    if (typeof lucide !== 'undefined') lucide.createIcons();
});