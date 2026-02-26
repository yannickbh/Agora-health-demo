// ── Config ───────────────────────────────────
const API_BASE = ""; // Relative to same origin
const CHANNEL = "hospital-support";
const USER_UID = Math.floor(Math.random() * 90000) + 10000;

let APP_ID = "";
let SELECTED_USE_CASE = "hospital";
let client, localTrack;

// Initialization
document.addEventListener("DOMContentLoaded", async () => {
    try {
        const [configRes, ucRes] = await Promise.all([
            fetch(`${API_BASE}/config`),
            fetch(`${API_BASE}/use_cases`),
        ]);
        if (!configRes.ok) throw new Error("Failed to load config");
        const configData = await configRes.json();
        APP_ID = configData.agora_app_id;

        if (ucRes.ok) {
            const ucData = await ucRes.json();
            populateUseCases(ucData.use_cases || []);
        }

        log("Configuração carregada. UID do usuário: " + USER_UID, "ok");
    } catch (e) {
        log("Falha ao carregar config.", "err");
        console.error("Failed to load config", e);
    }
});

function populateUseCases(useCases) {
    const select = document.getElementById("use-case-select");
    if (!select || useCases.length === 0) return;
    select.innerHTML = "";
    useCases.forEach(uc => {
        const opt = document.createElement("option");
        opt.value = uc.id;
        opt.textContent = uc.name;
        select.appendChild(opt);
    });
    SELECTED_USE_CASE = select.value;
    select.addEventListener("change", () => { SELECTED_USE_CASE = select.value; });
    document.getElementById("use-case-wrapper").style.display = "flex";
}

// ── Logging ─────────────────────────────────────────────────
function log(msg, type = "") {
    const logEl = document.getElementById("log");
    const now = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    const div = document.createElement("div");
    div.className = "entry " + type;
    div.innerHTML = `<span class="ts">${now}</span><span>${msg}</span>`;
    logEl.appendChild(div);
    logEl.scrollTop = logEl.scrollHeight;
    console.log(`[${type || 'info'}] ${msg}`);
}

// ── UI helpers ───────────────────────────────────────────────
function setStatus(text, state = "") {
    const badge = document.getElementById("statusBadge");
    badge.className = "status-badge " + state;
    document.getElementById("statusText").textContent = text;
}

function setAvatar(state) {
    const ring = document.getElementById("avatarRing");
    ring.className = "avatar-ring " + state;
}

// ── Start session ────────────────────────────────────────────
async function startSession() {
    if (!APP_ID) {
        log("❌ Erro: Configuração não carregada.", "err");
        return;
    }
    document.getElementById("btn-start").disabled = true;
    setStatus("Conectando...", "connecting");
    setAvatar("connecting");
    log("Iniciando assistente hospitalar...");

    try {
        // 1. Get RTC token for the user FIRST
        const tokenResp = await fetch(`${API_BASE}/token/${CHANNEL}/${USER_UID}`);
        if (!tokenResp.ok) throw new Error("Falha ao obter token RTC");
        const { token } = await tokenResp.json();
        log("Token RTC recebido");

        // 2. Create client and set up ALL event handlers BEFORE joining
        client = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" });

        // Set up event handlers BEFORE joining to catch all events
        client.on("user-joined", (user) => {
            log(`🔵 Usuário entrou no canal: UID=${user.uid}`, "ok");
        });

        client.on("user-left", (user, reason) => {
            log(`🔴 Usuário saiu: UID=${user.uid}, motivo=${reason}`);
            setAvatar("listening");
        });

        client.on("user-published", async (user, mediaType) => {
            log(`📡 user-published: UID=${user.uid}, tipo=${mediaType}`);
            try {
                await client.subscribe(user, mediaType);
                log(`✅ Inscrito no stream de UID=${user.uid} (${mediaType})`);
                if (mediaType === "audio") {
                    user.audioTrack.play();
                    setAvatar("speaking");
                    log("🔊 Reproduzindo áudio do agente...", "ok");
                }
            } catch (subErr) {
                log(`❌ Erro ao se inscrever: ${subErr.message}`, "err");
            }
        });

        client.on("user-unpublished", (user, mediaType) => {
            log(`📡 user-unpublished: UID=${user.uid}, tipo=${mediaType}`);
            setAvatar("listening");
        });

        client.on("connection-state-change", (curState, prevState) => {
            log(`🔗 Conexão: ${prevState} → ${curState}`);
        });

        // 3. Join the Agora channel
        await client.join(APP_ID, CHANNEL, token, USER_UID);
        log(`Canal Agora conectado (UID=${USER_UID})`);

        // 4. Publish microphone
        localTrack = await AgoraRTC.createMicrophoneAudioTrack();
        await client.publish([localTrack]);
        log("🎤 Microfone publicado");

        // 5. NOW start the ConvoAI agent (user is already in channel)
        const startResp = await fetch(`${API_BASE}/start`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ channel: CHANNEL, user_uid: USER_UID, use_case: SELECTED_USE_CASE }),
        });

        const startData = await startResp.json();
        if (!startResp.ok) {
            throw new Error(startData.detail || startResp.statusText);
        }

        log(`✅ Agente iniciado (ID: ${startData.agent_id.slice(0, 12)}...)`, "ok");

        // Update UI
        document.getElementById("btn-start").style.display = "none";
        document.getElementById("btn-stop").style.display = "flex";
        setStatus("Conectado — fale agora", "connected");
        setAvatar("listening");
        log("✅ Pronto! Faça sua pergunta.", "ok");

    } catch (err) {
        log("❌ Erro: " + err.message, "err");
        setStatus("Falha na conexão", "");
        setAvatar("");
        document.getElementById("btn-start").disabled = false;
        if (localTrack) { localTrack.stop(); localTrack.close(); localTrack = null; }
        if (client) { await client.leave(); client = null; }
    }
}

// ── Stop session ─────────────────────────────────────────────
async function stopSession() {
    log("Encerrando sessão...");
    try {
        await fetch(`${API_BASE}/stop/${CHANNEL}`, { method: "POST" });
        log("Agente parado", "ok");
    } catch (e) {
        log("Falha ao parar agente", "err");
    }

    if (localTrack) { localTrack.stop(); localTrack.close(); localTrack = null; }
    if (client) { await client.leave(); client = null; }

    document.getElementById("btn-stop").style.display = "none";
    document.getElementById("btn-start").style.display = "flex";
    document.getElementById("btn-start").disabled = false;
    setStatus("Pronto para conectar", "");
    setAvatar("");
    log("Sessão encerrada.");
}
