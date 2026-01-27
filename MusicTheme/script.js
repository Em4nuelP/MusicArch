/****************************************************
 * BLOCO 1 — STATE (estado global)
 ****************************************************/
let files = [];
let idx = 0;
let tracks = [];

let viewMode = "all"; // all | artists | albums | artistTracks | albumTracks
let viewFilter = null;
let searchQuery = "";

let accent = getComputedStyle(document.documentElement)
  .getPropertyValue("--accent")
  .trim() || "#ffffff";

let vizMode = "bars"; // "bars" | "line"


/****************************************************
 * BLOCO 2 — DOM (cache de elementos)
 ****************************************************/
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
const navButtons = Array.from(document.querySelectorAll(".plistNav .seg"));
const plistSub = document.getElementById("plistSub");
const backToList = document.getElementById("backToList");
const subTitle = document.getElementById("subTitle");
const searchInput = document.getElementById("searchInput");

const colorPicker = document.getElementById("colorPicker");
const vizSelect = document.getElementById("vizSelect");
const vizModeLabel = document.getElementById("vizMode");

const volume = document.getElementById("volume");
const muteBtn = document.getElementById("mute");

document.getElementById("selectFolder").onclick = () => folder.click();


/****************************************************
 * BLOCO 3 — ICONS (Lucide)
 ****************************************************/
function renderIcons() {
  if (window.lucide) window.lucide.createIcons();
}
renderIcons();

function setButtonIcon(buttonEl, iconName) {
  buttonEl.innerHTML = `<i data-lucide="${iconName}"></i>`;
  renderIcons();
}

function updatePlayIcon(isPlaying) {
  // play/pause no botão central
  playBtn.innerHTML = isPlaying
    ? `<i data-lucide="pause"></i>`
    : `<i data-lucide="play"></i>`;
  renderIcons();
}

function updateMuteIcon() {
  if (audio.muted || audio.volume === 0) setButtonIcon(muteBtn, "volume-x");
  else if (audio.volume < 0.5) setButtonIcon(muteBtn, "volume-1");
  else setButtonIcon(muteBtn, "volume-2");
}


/****************************************************
 * BLOCO 4 — HELPERS (utilitários)
 ****************************************************/
function fmtTime(s) {
  if (!isFinite(s) || s < 0) return "0:00";
  const m = Math.floor(s / 60);
  const r = Math.floor(s % 60);
  return `${m}:${String(r).padStart(2, "0")}`;
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (m) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m])
  );
}

function hexToRgba(hex, a) {
  const h = hex.replace("#", "").trim();
  const full = h.length === 3 ? h.split("").map(ch => ch + ch).join("") : h;
  const n = parseInt(full, 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  return `rgba(${r},${g},${b},${a})`;
}

function baseTitleFromFile(file) {
  return file.name.replace(/\.[^/.]+$/, "");
}

function readTags(file) {
  return new Promise((resolve) => {
    if (!window.jsmediatags) {
      resolve({ title: "", artist: "", album: "" });
      return;
    }
    window.jsmediatags.read(file, {
      onSuccess: (tag) => {
        const t = tag.tags || {};
        resolve({
          title: t.title || t.TIT2 || "",
          artist: t.artist || t.TPE1 || "",
          album: t.album || t.TALB || ""
        });
      },
      onError: () => resolve({ title: "", artist: "", album: "" })
    });
  });
}

function normalizeText(s) {
  return String(s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}


/****************************************************
 * BLOCO 5 — COVER FALLBACK + ID3 TAGS
 ****************************************************/
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

function loadTagsAndCover(file) {
  // limpa blob anterior da capa
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


/****************************************************
 * BLOCO 6 — ACCENT + VIZ MODE
 ****************************************************/
colorPicker.value = accent;
colorPicker.oninput = (e) => {
  accent = e.target.value;
  document.documentElement.style.setProperty("--accent", accent);
  if (!coverImg.dataset.blobUrl) setFallbackCover();
};

vizSelect.onchange = (e) => {
  vizMode = e.target.value;
  vizModeLabel.textContent = vizMode === "bars" ? "Barras" : "Linha";
};
vizModeLabel.textContent = "Barras";

document.getElementById("visualizer").addEventListener("click", () => {
  vizMode = (vizMode === "bars") ? "line" : "bars";
  vizSelect.value = vizMode;
  vizModeLabel.textContent = vizMode === "bars" ? "Barras" : "Linha";
});


/****************************************************
 * BLOCO 7 — VOLUME + MUTE
 ****************************************************/
audio.volume = 0.85;
volume.value = "85";
audio.muted = false;

volume.oninput = () => {
  audio.muted = false;
  audio.volume = Number(volume.value) / 100;
  updateMuteIcon();
};

muteBtn.onclick = () => {
  audio.muted = !audio.muted;
  updateMuteIcon();
};
updateMuteIcon();


/****************************************************
 * BLOCO 8 — PLAYLIST UI
 ****************************************************/
function setView(mode, filter = null) {
  viewMode = mode;
  viewFilter = filter;

  navButtons.forEach((btn) => {
    const target = btn.dataset.view;
    const active = (mode === "all" && target === "all")
      || (mode.startsWith("artist") && target === "artists")
      || (mode.startsWith("album") && target === "albums");
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-selected", active ? "true" : "false");
  });

  if (mode === "artistTracks") backToList.onclick = () => setView("artists");
  if (mode === "albumTracks") backToList.onclick = () => setView("albums");

  const inSub = mode === "artistTracks" || mode === "albumTracks";
  backToList.disabled = !inSub;
  backToList.setAttribute("aria-disabled", inSub ? "false" : "true");

  renderPlaylist();
}

navButtons.forEach((btn) => {
  btn.onclick = () => setView(btn.dataset.view);
});

searchInput.oninput = () => {
  searchQuery = normalizeText(searchInput.value);
  renderPlaylist();
};

function renderPlaylist() {
  playlist.innerHTML = "";

  const q = searchQuery;
  const matchesTrack = (t) => {
    if (!q) return true;
    const fileName = t.file ? t.file.name : "";
    const fileBase = fileName.replace(/\.[^/.]+$/, "");
    return (
      normalizeText(t.title).includes(q) ||
      normalizeText(t.artist).includes(q) ||
      normalizeText(t.album).includes(q) ||
      normalizeText(fileName).includes(q) ||
      normalizeText(fileBase).includes(q)
    );
  };

  const filteredTracks = tracks.filter(matchesTrack);

  const byArtist = () => {
    const map = new Map();
    filteredTracks.forEach((t) => {
      const key = t.artist || "Desconhecido";
      map.set(key, (map.get(key) || 0) + 1);
    });
    return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  };

  const byAlbum = () => {
    const map = new Map();
    filteredTracks.forEach((t) => {
      const key = t.album || "Desconhecido";
      map.set(key, (map.get(key) || 0) + 1);
    });
    return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  };

  const renderTracks = (list) => {
    list.forEach((t) => {
      const div = document.createElement("div");
      div.className = "track";
      div.dataset.index = String(t.index);
      div.innerHTML = `<span>${escapeHtml(t.title)}</span><span class="sub">${escapeHtml(t.artist || "Desconhecido")} - ${escapeHtml(t.album || "Desconhecido")}</span>`;
      div.onclick = () => { idx = t.index; playIndex(true); };
      playlist.appendChild(div);
    });
  };

  const setCount = (n) => { countEl.textContent = String(n); };

  plistSub.hidden = true;
  subTitle.textContent = "";

  if (viewMode === "all") {
    setCount(filteredTracks.length);
    renderTracks(filteredTracks);
  } else if (viewMode === "artists") {
    const items = byArtist();
    setCount(items.length);
    items.forEach(([name, total]) => {
      const div = document.createElement("div");
      div.className = "track group";
      div.innerHTML = `<span>${escapeHtml(name)}</span><span class="sub">${total} musica(s)</span>`;
      div.onclick = () => setView("artistTracks", name);
      playlist.appendChild(div);
    });
  } else if (viewMode === "albums") {
    const items = byAlbum();
    setCount(items.length);
    items.forEach(([name, total]) => {
      const div = document.createElement("div");
      div.className = "track group";
      div.innerHTML = `<span>${escapeHtml(name)}</span><span class="sub">${total} musica(s)</span>`;
      div.onclick = () => setView("albumTracks", name);
      playlist.appendChild(div);
    });
  } else if (viewMode === "artistTracks") {
    plistSub.hidden = false;
    subTitle.textContent = `Artista: ${viewFilter || "Desconhecido"}`;
    const list = filteredTracks.filter(t => (t.artist || "Desconhecido") === viewFilter);
    setCount(list.length);
    renderTracks(list);
  } else if (viewMode === "albumTracks") {
    plistSub.hidden = false;
    subTitle.textContent = `Album: ${viewFilter || "Desconhecido"}`;
    const list = filteredTracks.filter(t => (t.album || "Desconhecido") === viewFilter);
    setCount(list.length);
    renderTracks(list);
  }

  updateActive();
}

function updateActive() {
  document.querySelectorAll(".track").forEach((el) => {
    const dataIndex = Number(el.dataset.index);
    if (Number.isNaN(dataIndex)) {
      el.classList.remove("active");
      return;
    }
    el.classList.toggle("active", dataIndex === idx);
  });
}


/****************************************************
 * BLOCO 9 — AUDIO URL (evita vazamento de objectURL)
 ****************************************************/
let lastAudioUrl = null;

function setAudioSrcFromFile(file) {
  if (lastAudioUrl) URL.revokeObjectURL(lastAudioUrl);
  lastAudioUrl = URL.createObjectURL(file);
  audio.src = lastAudioUrl;
}


/****************************************************
 * BLOCO 10 — PLAYER (play/pause/next/prev)
 ****************************************************/
function playIndex(userGesture = false) {
  if (!files.length) return;

  const f = files[idx];
  setAudioSrcFromFile(f);

  const t = tracks[idx];
  musicName.textContent = (t && t.title) ? t.title : f.name;
  statusEl.textContent = "Carregando…";
  loadTagsAndCover(f);

  if (userGesture) resumeAudioCtx();

  audio.play().then(() => {
    updatePlayIcon(true);
    statusEl.textContent = "Reproduzindo";
    updateActive();
  }).catch(() => {
    updatePlayIcon(false);
    statusEl.textContent = "Clique em ▶ para iniciar (política do navegador).";
  });
}

playBtn.onclick = () => {
  if (!files.length) return;
  resumeAudioCtx();

  if (audio.paused) {
    audio.play().then(() => {
      updatePlayIcon(true);
      statusEl.textContent = "Reproduzindo";
    }).catch(() => {
      statusEl.textContent = "Sem permissão para autoplay.";
    });
  } else {
    audio.pause();
    updatePlayIcon(false);
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
  tracks = files.map((f, i) => ({
    file: f,
    index: i,
    title: baseTitleFromFile(f),
    artist: "",
    album: ""
  }));
  setView("all");
  statusEl.textContent = files.length ? "Carregando metadados..." : "Nenhum áudio encontrado.";

  // garante ícone inicial
  updatePlayIcon(false);

  if (files.length) playIndex(false);

  if (!files.length) return;
  Promise.all(tracks.map((t) => readTags(t.file))).then((tags) => {
    tags.forEach((tag, i) => {
      if (!tracks[i]) return;
      tracks[i].title = tag.title || tracks[i].title;
      tracks[i].artist = tag.artist || "";
      tracks[i].album = tag.album || "";
    });
    renderPlaylist();
    statusEl.textContent = "Pronto para tocar.";
  });
};

audio.onended = () => {
  if (!files.length) return;
  idx = (idx + 1) % files.length;
  playIndex(true);
};


/****************************************************
 * BLOCO 11 — PROGRESS + TEMPOS (AGORA EM CIMA)
 ****************************************************/
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


/****************************************************
 * BLOCO 12 — KEYBOARD SHORTCUTS
 ****************************************************/
window.addEventListener("keydown", (e) => {
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


/****************************************************
 * BLOCO 13 — VISUALIZER (canvas + analyser)
 ****************************************************/
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
  analyser.fftSize = 1024;
  srcNode = audioCtx.createMediaElementSource(audio);
  srcNode.connect(analyser);
  analyser.connect(audioCtx.destination);

  freqData = new Uint8Array(analyser.frequencyBinCount);
  timeData = new Uint8Array(analyser.fftSize);
}
function resumeAudioCtx() {
  initAudioGraph();
  if (audioCtx && audioCtx.state === "suspended") audioCtx.resume();
}

function roundRect(c, x, y, w, h, r) {
  c.beginPath();
  c.moveTo(x + r, y);
  c.arcTo(x + w, y, x + w, y + h, r);
  c.arcTo(x + w, y + h, x, y + h, r);
  c.arcTo(x, y + h, x, y, r);
  c.arcTo(x, y, x + w, y, r);
  c.closePath();
}

function drawIdle(W, H) {
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

  // usa só até 70% do espectro (mais musical)
  const usableBins = Math.floor(freqData.length * 0.7);
  const step = Math.max(1, Math.floor(usableBins / bars));

  const gap = 6;
  const barW = Math.max(2, (W - (bars + 1) * gap) / bars);

  ctx.save();
  ctx.shadowColor = accent;
  ctx.shadowBlur = 16;

  for (let i = 0; i < bars; i++) {
    const index = i * step;
    const v = freqData[index] / 255;

    // ganho leve para as últimas barras
    const gain = 0.6 + i / bars;
    const h = Math.max(4, v * gain * (H * 0.82));

    const x = gap + i * (barW + gap);
    const y = H - h - 12;

    const g = ctx.createLinearGradient(0, y, 0, y + h);
    g.addColorStop(0, hexToRgba(accent, 0.95));
    g.addColorStop(1, "rgba(255,255,255,0.10)");

    roundRect(ctx, x, y, barW, h, 10);
    ctx.fillStyle = g;
    ctx.fill();
  }
  ctx.restore();
}


// ===== Line visualizer tuning =====
const LINE_SMOOTHING = 0.18;   // 0.05 (muito calmo) → 0.2 (mais vivo)
const LINE_AMPLITUDE = 0.15;   // porcentagem da altura do canvas


let smoothLine = null;

function drawLine(W, H){
  analyser.getByteTimeDomainData(timeData);

  if (!smoothLine || smoothLine.length !== timeData.length) {
    smoothLine = new Float32Array(timeData.length);
    for (let i = 0; i < timeData.length; i++) {
      smoothLine[i] = timeData[i];
    }
  }

  ctx.save();
  ctx.shadowColor = accent;
  ctx.shadowBlur = 8;

  ctx.lineWidth = 2;
  ctx.strokeStyle = hexToRgba(accent, 0.85);

  const mid = H / 2;
  const amp = H * LINE_AMPLITUDE; // ✅ agora correto

  ctx.beginPath();

  for (let i = 0; i < timeData.length; i++) {
    smoothLine[i] += (timeData[i] - smoothLine[i]) * LINE_SMOOTHING;

    const t = smoothLine[i] / 128.0 - 1.0;
    const x = (i / (timeData.length - 1)) * (W - 24) + 12;
    const y = mid + t * amp;

    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }

  ctx.stroke();

  // linha base discreta
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


function drawFrame(W, H) {
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

  ctx.fillStyle = "rgba(0,0,0,0.08)";
  ctx.fillRect(0, 0, W, H);

  drawFrame(W, H);

  if (!analyser) { drawIdle(W, H); return; }
  if (audio.paused || audio.muted || audio.volume === 0) { drawIdle(W, H); return; }

  if (vizMode === "line") drawLine(W, H);
  else drawBars(W, H);
}
draw();
