let files = [];
let idx = 0;

let accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#66e6b3";
let vizMode = "bars"; // "bars" | "line"

const audio = document.getElementById("audio");
const folder = document.getElementById("folder");
const playlist = document.getElementById("playlist");
const countEl = document.getElementById("count");
const musicName = document.getElementById("musicName");
const musicArtist = document.getElementById("musicArtist");
const coverImg = document.getElementById("coverImg");
const progress = document.getElementById("progress");
const playBtn = document.getElementById("play");
const statusEl = document.getElementById("status");
const tCur = document.getElementById("tCur");
const tDur = document.getElementById("tDur");

const colorPicker = document.getElementById("colorPicker");
const vizSelect = document.getElementById("vizSelect");
const vizModeLabel = document.getElementById("vizMode");

const volume = document.getElementById("volume");
const muteBtn = document.getElementById("mute");

document.getElementById("selectFolder").onclick = () => folder.click();

/* ====== Accent color ====== */
colorPicker.value = accent;
colorPicker.oninput = (e) => {
  accent = e.target.value;
  document.documentElement.style.setProperty("--accent", accent);
  // atualiza fallback (fica bem coerente)
  if (!coverImg.dataset.blobUrl) setFallbackCover();
};

/* ====== Viz mode ====== */
vizSelect.onchange = (e) => {
  vizMode = e.target.value;
  vizModeLabel.textContent = vizMode === "bars" ? "Barras" : "Linha";
};
vizModeLabel.textContent = "Barras";

/* Clique no canvas alterna modo (bem útil) */
document.getElementById("visualizer").addEventListener("click", () => {
  vizMode = (vizMode === "bars") ? "line" : "bars";
  vizSelect.value = vizMode;
  vizModeLabel.textContent = vizMode === "bars" ? "Barras" : "Linha";
});

/* ====== Volume ====== */
audio.volume = 0.85;
volume.value = "85";

volume.oninput = () => {
  audio.muted = false;
  const v = Number(volume.value) / 100;
  audio.volume = v;
  updateMuteIcon();
};

muteBtn.onclick = () => {
  audio.muted = !audio.muted;
  updateMuteIcon();
};

function updateMuteIcon(){
  // simples e limpo
  if (audio.muted || audio.volume === 0) muteBtn.textContent = "🔇";
  else if (audio.volume < 0.5) muteBtn.textContent = "🔉";
  else muteBtn.textContent = "🔈";
}
updateMuteIcon();

/* ===== Helpers ===== */
function fmtTime(s) {
  if (!isFinite(s) || s < 0) return "0:00";
  const m = Math.floor(s / 60);
  const r = Math.floor(s % 60);
  return `${m}:${String(r).padStart(2, "0")}`;
}
function escapeHtml(s){
  return s.replace(/[&<>"']/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
}
function hexToRgba(hex, a){
  const h = hex.replace("#","").trim();
  const full = h.length === 3 ? h.split("").map(ch => ch+ch).join("") : h;
  const n = parseInt(full, 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  return `rgba(${r},${g},${b},${a})`;
}

/* ===== Fallback cover (Air-like) ===== */
function setFallbackCover() {
  const svg = `
  <svg xmlns="http://www.w3.org/2000/svg" width="600" height="600">
    <defs>
      <radialGradient id="g1" cx="30%" cy="25%" r="70%">
        <stop offset="0" stop-color="${accent}" stop-opacity="0.45"/>
        <stop offset="1" stop-color="#ffffff" stop-opacity="0.05"/>
      </radialGradient>
      <radialGradient id="g2" cx="70%" cy="75%" r="70%">
        <stop offset="0" stop-color="#9fb9ff" stop-opacity="0.35"/>
        <stop offset="1" stop-color="#000000" stop-opacity="0.0"/>
      </radialGradient>
    </defs>
    <rect width="600" height="600" rx="60" fill="rgba(255,255,255,0.06)"/>
    <circle cx="210" cy="170" r="220" fill="url(#g1)"/>
    <circle cx="420" cy="420" r="260" fill="url(#g2)"/>
    <circle cx="300" cy="320" r="140" fill="rgba(0,0,0,0.18)"/>
    <circle cx="300" cy="320" r="55" fill="rgba(255,255,255,0.14)"/>
  </svg>`;
  coverImg.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  delete coverImg.dataset.blobUrl;
}

/* ===== ID3: capa + artista/álbum ===== */
function loadTagsAndCover(file) {
  // limpa blob anterior
  if (coverImg.dataset.blobUrl) {
    URL.revokeObjectURL(coverImg.dataset.blobUrl);
    delete coverImg.dataset.blobUrl;
  }

  setFallbackCover();
  musicArtist.textContent = "Arquivo local";

  if (!window.jsmediatags) return;

  window.jsmediatags.read(file, {
    onSuccess: (tag) => {
      const t = tag.tags || {};
      const artist = t.artist || t.TPE1 || "";
      const album = t.album || t.TALB || "";
      const title = t.title || t.TIT2 || "";

      if (title) musicName.textContent = title;
      if (artist || album) musicArtist.textContent = [artist, album].filter(Boolean).join(" — ");

      const pic = t.picture;
      if (!pic) return;

      const bytes = new Uint8Array(pic.data);
      const blob = new Blob([bytes], { type: pic.format || "image/jpeg" });
      const url = URL.createObjectURL(blob);

      coverImg.src = url;
      coverImg.dataset.blobUrl = url;
    },
    onError: () => { /* mantém fallback */ }
  });
}

/* ===== Playlist ===== */
function renderPlaylist() {
  playlist.innerHTML = "";
  countEl.textContent = String(files.length);

  files.forEach((f, i) => {
    const div = document.createElement("div");
    div.className = "track";
    div.innerHTML = `<span>${escapeHtml(f.name)}</span><span class="sub">Local</span>`;
    div.onclick = () => { idx = i; playIndex(true); };
    playlist.appendChild(div);
  });
  updateActive();
}
function updateActive() {
  document.querySelectorAll(".track").forEach((el, i) => {
    el.classList.toggle("active", i === idx);
  });
}

/* ===== Audio play logic ===== */
function playIndex(userGesture = false) {
  if (!files.length) return;

  const f = files[idx];
  audio.src = URL.createObjectURL(f);

  // nome inicial (antes do ID3)
  musicName.textContent = f.name;
  statusEl.textContent = "Carregando…";

  loadTagsAndCover(f);

  if (userGesture) resumeAudioCtx();

  audio.play().then(() => {
    playBtn.textContent = "⏸";
    statusEl.textContent = "Reproduzindo";
    updateActive();
  }).catch(() => {
    // caso o navegador bloqueie autoplay em algumas situações
    playBtn.textContent = "▶";
    statusEl.textContent = "Clique em ▶ para iniciar (política do navegador).";
  });
}

playBtn.onclick = () => {
  if (!files.length) return;
  resumeAudioCtx();

  if (audio.paused) {
    audio.play().then(() => {
      playBtn.textContent = "⏸";
      statusEl.textContent = "Reproduzindo";
    }).catch(() => {
      statusEl.textContent = "Sem permissão para autoplay.";
    });
  } else {
    audio.pause();
    playBtn.textContent = "▶";
    statusEl.textContent = "Pausado";
  }
};

document.getElementById("next").onclick = () => {
  if (!files.length) return;
  idx = (idx + 1) % files.length;
  playIndex(true);
};

document.getElementById("prev").onclick = () => {
  if (!files.length) return;
  idx = (idx - 1 + files.length) % files.length;
  playIndex(true);
};

folder.onchange = (e) => {
  files = Array.from(e.target.files).filter(f => f.type.startsWith("audio/"));
  idx = 0;
  renderPlaylist();
  statusEl.textContent = files.length ? "Pronto para tocar." : "Nenhum áudio encontrado.";
  if (files.length) playIndex(false);
};

audio.onended = () => {
  if (!files.length) return;
  idx = (idx + 1) % files.length;
  playIndex(true);
};

audio.onloadedmetadata = () => {
  tDur.textContent = fmtTime(audio.duration);
};

audio.ontimeupdate = () => {
  progress.value = (audio.currentTime / audio.duration) * 100 || 0;
  tCur.textContent = fmtTime(audio.currentTime);
};

progress.oninput = () => {
  if (!isFinite(audio.duration)) return;
  audio.currentTime = (progress.value / 100) * audio.duration;
};

/* ===== Keyboard shortcuts ===== */
window.addEventListener("keydown", (e) => {
  // evita interferir quando estiver mexendo em input
  const tag = (document.activeElement?.tagName || "").toLowerCase();
  if (tag === "input" || tag === "select" || tag === "textarea") return;

  if (e.code === "Space") {
    e.preventDefault();
    playBtn.click();
  } else if (e.code === "ArrowRight") {
    document.getElementById("next").click();
  } else if (e.code === "ArrowLeft") {
    document.getElementById("prev").click();
  } else if (e.key.toLowerCase() === "m") {
    muteBtn.click();
  }
});

/* ===== Visualizer ===== */
const canvas = document.getElementById("visualizer");
const ctx = canvas.getContext("2d");

function resizeCanvas() {
  canvas.width = canvas.clientWidth * devicePixelRatio;
  canvas.height = canvas.clientHeight * devicePixelRatio;
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
}
window.addEventListener("resize", resizeCanvas);
resizeCanvas();

let audioCtx, analyser, srcNode, freqData, timeData;

function initAudioGraph() {
  if (audioCtx) return;
  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 1024; // melhor p/ linha suave
  srcNode = audioCtx.createMediaElementSource(audio);
  srcNode.connect(analyser);
  analyser.connect(audioCtx.destination);

  freqData = new Uint8Array(analyser.frequencyBinCount);
  timeData = new Uint8Array(analyser.fftSize);
}
function resumeAudioCtx(){
  initAudioGraph();
  if (audioCtx && audioCtx.state === "suspended") audioCtx.resume();
}

function roundRect(c, x, y, w, h, r){
  c.beginPath();
  c.moveTo(x + r, y);
  c.arcTo(x + w, y, x + w, y + h, r);
  c.arcTo(x + w, y + h, x, y + h, r);
  c.arcTo(x, y + h, x, y, r);
  c.arcTo(x, y, x + w, y, r);
  c.closePath();
}

function drawIdle(W, H){
  ctx.globalAlpha = 0.35;
  ctx.strokeStyle = "rgba(255,255,255,0.20)";
  ctx.lineWidth = 1;

  ctx.beginPath();
  ctx.moveTo(18, H / 2);
  ctx.lineTo(W - 18, H / 2);
  ctx.stroke();

  ctx.globalAlpha = 1;
}

function drawBars(W, H){
  analyser.getByteFrequencyData(freqData);

  const bars = 60;
  const step = Math.floor(freqData.length / bars);
  const gap = 6;
  const barW = Math.max(2, (W - (bars + 1) * gap) / bars);

  ctx.save();
  ctx.shadowColor = accent;
  ctx.shadowBlur = 14;

  for (let i = 0; i < bars; i++) {
    const v = freqData[i * step] / 255;
    const h = Math.max(3, v * (H * 0.82));
    const x = gap + i * (barW + gap);
    const y = H - h - 12;

    const g = ctx.createLinearGradient(0, y, 0, y + h);
    g.addColorStop(0, hexToRgba(accent, 0.95));
    g.addColorStop(1, "rgba(255,255,255,0.12)");

    roundRect(ctx, x, y, barW, h, 10);
    ctx.fillStyle = g;
    ctx.fill();
  }
  ctx.restore();
}

function drawLine(W, H){
  analyser.getByteTimeDomainData(timeData);

  // linha central com glow sutil
  ctx.save();
  ctx.shadowColor = accent;
  ctx.shadowBlur = 10;

  ctx.lineWidth = 2;
  ctx.strokeStyle = hexToRgba(accent, 0.85);

  const mid = H / 2;
  const amp = H * 0.33;

  ctx.beginPath();
  for (let i = 0; i < timeData.length; i++) {
    const t = timeData[i] / 128.0 - 1.0; // -1..1
    const x = (i / (timeData.length - 1)) * (W - 24) + 12;
    const y = mid + t * amp;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();

  // uma “linha base” bem discreta por baixo (fica bem Air)
  ctx.shadowBlur = 0;
  ctx.globalAlpha = 0.35;
  ctx.strokeStyle = "rgba(255,255,255,0.18)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(12, mid);
  ctx.lineTo(W - 12, mid);
  ctx.stroke();

  ctx.restore();
  ctx.globalAlpha = 1;
}

function drawFrame(W, H){
  ctx.globalAlpha = 0.35;
  ctx.strokeStyle = "rgba(255,255,255,0.18)";
  ctx.lineWidth = 1;
  roundRect(ctx, 10, 10, W - 20, H - 20, 16);
  ctx.stroke();
  ctx.globalAlpha = 1;
}

function draw() {
  requestAnimationFrame(draw);

  const W = canvas.clientWidth;
  const H = canvas.clientHeight;

    ctx.clearRect(0, 0, W, H);

  // fundo levemente “glass”
  ctx.fillStyle = "rgba(0,0,0,0.08)";
  ctx.fillRect(0, 0, W, H);

  // moldura
  drawFrame(W, H);

  // se ainda não iniciou o grafo de áudio, mostra idle
  if (!analyser) {
    drawIdle(W, H);
    return;
  }

  // quando estiver pausado, desenha algo bem discreto (idle)
  if (audio.paused || audio.muted || audio.volume === 0) {
    drawIdle(W, H);
    return;
  }

  // desenha o visualizer
  if (vizMode === "line") drawLine(W, H);
  else drawBars(W, H);
}

// inicia o loop do canvas
draw();

/* ===== Melhorias pequenas (opcional) =====
   - garante que ao trocar de música não acumule objectURL do áudio
*/
let lastAudioUrl = null;

function setAudioSrcFromFile(file) {
  // limpa URL anterior do <audio>
  if (lastAudioUrl) URL.revokeObjectURL(lastAudioUrl);

  lastAudioUrl = URL.createObjectURL(file);
  audio.src = lastAudioUrl;
}

/* Troca no playIndex pra usar o helper acima */
const _playIndexOriginal = playIndex;
playIndex = function (userGesture = false) {
  if (!files.length) return;

  const f = files[idx];
  setAudioSrcFromFile(f);

  // nome inicial (antes do ID3)
  musicName.textContent = f.name;
  statusEl.textContent = "Carregando…";

  loadTagsAndCover(f);

  if (userGesture) resumeAudioCtx();

  audio
    .play()
    .then(() => {
      playBtn.textContent = "⏸";
      statusEl.textContent = "Reproduzindo";
      updateActive();
    })
    .catch(() => {
      playBtn.textContent = "▶";
      statusEl.textContent = "Clique em ▶ para iniciar (política do navegador).";
    });
};

