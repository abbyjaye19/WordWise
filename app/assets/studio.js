/* WordWise Reading Studio — browser side.
 * Draws the reading into #reader (one <span class="w"> per word), and runs the
 * reading tools: read aloud with word highlighting, tap-a-word, highlighter,
 * reading ruler, and one-paragraph focus. Talks to Dash with set_props.
 */
(function () {
  "use strict";

  const WW = (window.WW = {});
  const state = { mode: "lookup", color: "gold", start: null, ruler: false, focus: false };
  const synth = window.speechSynthesis || null;
  let run = 0; // bumps on every stop so old speech callbacks are ignored
  let speaking = false;
  let paused = false;

  const $ = (sel) => document.querySelector(sel);
  const reader = () => document.getElementById("reader");
  const paras = () => Array.from(document.querySelectorAll("#reader .r-p"));
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const bare = (s) => s.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, "");
  const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function setProps(id, props) {
    if (window.dash_clientside && window.dash_clientside.set_props) {
      window.dash_clientside.set_props(id, props);
    }
  }

  /* ---------- render ---------- */
  function docKey(doc) {
    return doc.title + "|" + JSON.stringify(doc.sections).length + "|" + doc.sections.length;
  }

  WW.render = function (doc) {
    const el = reader();
    if (!el) return;
    if (!doc || !doc.sections) {
      stop();
      el.innerHTML = "";
      el.dataset.key = "";
      pushHighlights();
      return;
    }
    const key = docKey(doc);
    if (el.dataset.key === key && el.querySelector(".w")) {
      // Same reading (e.g. just saved): keep what's on screen, only sync highlights.
      if (doc.highlights) applyHighlights(doc.highlights);
      return;
    }
    stop();
    let html = "";
    let pi = 0;
    let wi = 0;
    const many = doc.sections.length > 1;
    doc.sections.forEach((s, si) => {
      html += `<section class="r-section" data-s="${si}">`;
      if (many) html += `<h3 class="r-label">${esc(s.label)}</h3>`;
      s.paragraphs.forEach((p) => {
        let out = "";
        let last = 0;
        const re = /\S+/g;
        let m;
        while ((m = re.exec(p))) {
          out += esc(p.slice(last, m.index));
          out += `<span class="w" data-i="${wi++}" data-o="${m.index}">${esc(m[0])}</span>`;
          last = m.index + m[0].length;
        }
        out += esc(p.slice(last));
        html += `<p class="r-p" data-p="${pi++}">${out}</p>`;
      });
      html += "</section>";
    });
    el.innerHTML = html;
    el.dataset.key = key;
    el.classList.toggle("focus-mode", state.focus);
    state.start = null;
    applyHighlights(doc.highlights || {});
  };

  /* ---------- highlights (saved with the reading, used by downloads) ---------- */
  const HL = ["hl-gold", "hl-green", "hl-blue"];

  function applyHighlights(map) {
    document.querySelectorAll("#reader .w").forEach((w) => {
      w.classList.remove(...HL);
      const c = map[w.dataset.i];
      if (c) w.classList.add("hl-" + c);
    });
    pushHighlights();
  }

  let pushTimer = null;
  function pushHighlights() {
    clearTimeout(pushTimer);
    pushTimer = setTimeout(() => {
      const map = {};
      document.querySelectorAll("#reader .hl-gold, #reader .hl-green, #reader .hl-blue").forEach((w) => {
        map[w.dataset.i] = w.classList.contains("hl-gold") ? "gold" : w.classList.contains("hl-green") ? "green" : "blue";
      });
      setProps("highlights-store", { data: map });
    }, 150);
  }

  /* ---------- helpers ---------- */
  function sentences(text) {
    // [{start, end}] for each sentence in the text
    const out = [];
    const re = /[^.!?]+(?:[.!?]+["'”’)\]]*)?\s*/g;
    let m;
    while ((m = re.exec(text))) {
      if (!m[0]) break;
      out.push({ start: m.index, end: m.index + m[0].length });
    }
    return out.length ? out : [{ start: 0, end: text.length }];
  }

  function sentenceAround(pEl, offset) {
    const text = pEl.textContent;
    const s = sentences(text).find((x) => offset >= x.start && offset < x.end);
    return s ? text.slice(s.start, s.end).trim() : text;
  }

  function setCurrent(pEl) {
    paras().forEach((p) => p.classList.toggle("r-current", p === pEl));
  }

  function wordAt(pEl, charIndex) {
    let found = null;
    for (const w of pEl.querySelectorAll(".w")) {
      if (+w.dataset.o <= charIndex) found = w;
      else break;
    }
    return found;
  }

  function scrollIntoViewIfNeeded(el) {
    const r = el.getBoundingClientRect();
    if (r.top < 140 || r.bottom > window.innerHeight - 40) {
      el.scrollIntoView({ block: "center", behavior: reducedMotion() ? "auto" : "smooth" });
    }
  }

  /* ---------- read aloud ---------- */
  function pickVoice() {
    if (!synth) return null;
    const voices = synth.getVoices().filter((v) => /^en/i.test(v.lang));
    return (
      voices.find((v) => /natural/i.test(v.name) && /en-US/i.test(v.lang)) ||
      voices.find((v) => v.localService && /en-US/i.test(v.lang)) ||
      voices.find((v) => v.default) ||
      voices[0] ||
      null
    );
  }

  function rate() {
    const sel = document.getElementById("tts-rate");
    return sel ? parseFloat(sel.value) || 1 : 1;
  }

  function clearSpeaking() {
    document.querySelectorAll("#reader .w-speaking").forEach((w) => w.classList.remove("w-speaking"));
    document.querySelectorAll("#reader .r-reading").forEach((p) => p.classList.remove("r-reading"));
  }

  function speakFrom(pEl, offset) {
    if (!synth) {
      alert("Read aloud isn't available in this browser. Try Chrome or Edge.");
      return;
    }
    stop();
    const myRun = ++run;
    speaking = true;
    paused = false;
    updateButtons();
    const all = paras();
    let pIndex = all.indexOf(pEl);

    const speakPara = (p, startAt) => {
      if (myRun !== run) return;
      clearSpeaking();
      p.classList.add("r-reading");
      setCurrent(p);
      scrollIntoViewIfNeeded(p);
      const text = p.textContent;
      const chunks = sentences(text).filter((c) => c.end > startAt);
      if (chunks.length) chunks[0] = { start: Math.max(chunks[0].start, startAt), end: chunks[0].end };
      let ci = 0;
      const next = () => {
        if (myRun !== run) return;
        if (ci >= chunks.length) {
          pIndex += 1;
          if (pIndex < all.length) speakPara(all[pIndex], 0);
          else stop();
          return;
        }
        const c = chunks[ci++];
        const u = new SpeechSynthesisUtterance(text.slice(c.start, c.end));
        const v = pickVoice();
        if (v) u.voice = v;
        u.rate = rate();
        u.onboundary = (ev) => {
          if (myRun !== run || (ev.name && ev.name !== "word")) return;
          const w = wordAt(p, c.start + ev.charIndex);
          if (!w) return;
          p.querySelectorAll(".w-speaking").forEach((x) => x.classList.remove("w-speaking"));
          w.classList.add("w-speaking");
          if (state.ruler) moveRulerTo(w);
        };
        u.onend = next;
        u.onerror = () => {
          if (myRun === run) next();
        };
        synth.speak(u);
      };
      next();
    };
    speakPara(pEl, offset);
  }

  function play() {
    if (synth && paused) {
      synth.resume();
      paused = false;
      updateButtons();
      return;
    }
    const all = paras();
    if (!all.length) return;
    const w = state.start && document.body.contains(state.start) ? state.start : null;
    if (w) speakFrom(w.closest(".r-p"), +w.dataset.o);
    else speakFrom(all[0], 0);
  }

  function pause() {
    if (synth && speaking && !paused) {
      synth.pause();
      paused = true;
      updateButtons();
    }
  }

  function stop() {
    run += 1;
    if (synth) synth.cancel();
    speaking = false;
    paused = false;
    clearSpeaking();
    updateButtons();
    const r = document.getElementById("ww-ruler");
    if (r) r.hidden = true;
  }

  function sayText(text) {
    if (!synth || !text) return;
    stop();
    const u = new SpeechSynthesisUtterance(text);
    const v = pickVoice();
    if (v) u.voice = v;
    u.rate = rate();
    synth.speak(u);
  }

  function updateButtons() {
    const playBtn = document.getElementById("tts-play");
    if (playBtn) playBtn.textContent = paused ? "▶ Resume" : "▶ Read aloud";
    const pauseBtn = document.getElementById("tts-pause");
    if (pauseBtn) pauseBtn.setAttribute("aria-pressed", paused ? "true" : "false");
  }

  /* ---------- word actions ---------- */
  function lookup(w) {
    const word = bare(w.textContent);
    if (!word) return;
    document.querySelectorAll("#reader .w-active").forEach((x) => x.classList.remove("w-active"));
    w.classList.add("w-active");
    const p = w.closest(".r-p");
    setCurrent(p);
    setProps("word-request", { data: { word: word, sentence: sentenceAround(p, +w.dataset.o), t: Date.now() } });
  }

  function highlight(w, forceOn) {
    const cls = "hl-" + state.color;
    const had = w.classList.contains(cls);
    w.classList.remove("hl-gold", "hl-green", "hl-blue");
    if (forceOn || !had) w.classList.add(cls);
    pushHighlights();
  }

  function setMode(mode) {
    state.mode = mode;
    ["lookup", "highlight", "read"].forEach((m) => {
      const b = document.getElementById("mode-" + m);
      if (b) b.setAttribute("aria-pressed", m === mode ? "true" : "false");
    });
    const el = reader();
    if (el) el.dataset.mode = mode;
  }

  function setColor(color) {
    state.color = color;
    ["gold", "green", "blue"].forEach((c) => {
      const b = document.getElementById("color-" + c);
      if (b) b.setAttribute("aria-pressed", c === color ? "true" : "false");
    });
    setMode("highlight");
  }

  /* ---------- ruler + focus ---------- */
  function rulerEl() {
    let r = document.getElementById("ww-ruler");
    if (!r) {
      r = document.createElement("div");
      r.id = "ww-ruler";
      r.setAttribute("aria-hidden", "true");
      document.body.appendChild(r);
    }
    return r;
  }

  function moveRulerTo(target) {
    const el = reader();
    if (!el) return;
    const box = el.getBoundingClientRect();
    const t = target.getBoundingClientRect();
    const r = rulerEl();
    const h = Math.max(t.height * 1.5, 32);
    r.style.left = box.left + "px";
    r.style.width = box.width + "px";
    r.style.height = h + "px";
    r.style.top = t.top + t.height / 2 - h / 2 + "px";
    r.hidden = false;
  }

  function toggle(id, key) {
    state[key] = !state[key];
    const b = document.getElementById(id);
    if (b) b.setAttribute("aria-pressed", state[key] ? "true" : "false");
    if (key === "focus") {
      const el = reader();
      if (el) el.classList.toggle("focus-mode", state.focus);
      if (state.focus && !document.querySelector("#reader .r-current") && paras()[0]) setCurrent(paras()[0]);
    }
    if (key === "ruler") rulerEl().hidden = true;
  }

  /* ---------- events (delegated, so they work after Dash re-renders) ---------- */
  document.addEventListener("click", (e) => {
    const t = e.target;
    const w = t.closest && t.closest("#reader .w");
    if (w) {
      const sel = window.getSelection();
      if (sel && !sel.isCollapsed && sel.toString().trim().includes(" ")) return; // a drag-select, not a tap
      state.start = w;
      if (state.mode === "highlight") highlight(w);
      else if (state.mode === "read") speakFrom(w.closest(".r-p"), +w.dataset.o);
      else lookup(w);
      return;
    }
    const btn = t.closest && t.closest("button");
    if (!btn) return;
    switch (btn.id) {
      case "tts-play": return play();
      case "tts-pause": return paused ? play() : pause();
      case "tts-stop": return stop();
      case "mode-lookup": return setMode("lookup");
      case "mode-highlight": return setMode("highlight");
      case "mode-read": return setMode("read");
      case "color-gold": return setColor("gold");
      case "color-green": return setColor("green");
      case "color-blue": return setColor("blue");
      case "tool-clear":
        document.querySelectorAll("#reader .hl-gold, #reader .hl-green, #reader .hl-blue").forEach((x) => x.classList.remove("hl-gold", "hl-green", "hl-blue"));
        pushHighlights();
        return;
      case "export-print":
        stop();
        window.print();
        return;
      case "tool-ruler": return toggle("tool-ruler", "ruler");
      case "tool-focus": return toggle("tool-focus", "focus");
      case "studio-settings": {
        const open = document.getElementById("a11y-open");
        if (open) open.click();
        return;
      }
    }
    if (btn.classList.contains("speak-btn")) sayText(btn.dataset.say);
  });

  // Selecting a phrase: send it to the help panel, or highlight it in highlight mode.
  function onSelectEnd() {
    const sel = window.getSelection();
    const el = reader();
    if (!sel || sel.isCollapsed || !el || !sel.rangeCount) return;
    const range = sel.getRangeAt(0);
    if (!el.contains(range.commonAncestorContainer)) return;
    const text = sel.toString().replace(/\s+/g, " ").trim();
    if (!text || !text.includes(" ")) return;
    if (state.mode === "highlight") {
      el.querySelectorAll(".w").forEach((w) => {
        if (range.intersectsNode(w)) highlight(w, true);
      });
      sel.removeAllRanges();
      return;
    }
    setProps("selection-store", { data: { text: text.slice(0, 3000), t: Date.now() } });
  }
  document.addEventListener("mouseup", () => setTimeout(onSelectEnd, 0));
  document.addEventListener("keyup", (e) => { if (e.shiftKey) onSelectEnd(); });
  document.addEventListener("touchend", () => setTimeout(onSelectEnd, 50));

  document.addEventListener("mousemove", (e) => {
    const el = reader();
    if (!el) return;
    if (state.focus) {
      const p = e.target.closest && e.target.closest("#reader .r-p");
      if (p && !speaking) setCurrent(p);
    }
    if (!state.ruler || speaking) return;
    const box = el.getBoundingClientRect();
    const r = rulerEl();
    if (e.clientY < box.top || e.clientY > box.bottom || e.clientX < box.left || e.clientX > box.right) {
      r.hidden = true;
      return;
    }
    const h = 40;
    r.style.left = box.left + "px";
    r.style.width = box.width + "px";
    r.style.height = h + "px";
    r.style.top = e.clientY - h / 2 + "px";
    r.hidden = false;
  });

  document.addEventListener("scroll", () => {
    const r = document.getElementById("ww-ruler");
    if (r && !speaking) r.hidden = true;
  }, { passive: true });

  // Stop talking when the user leaves the studio page.
  window.addEventListener("popstate", stop);
  document.addEventListener("click", (e) => {
    const a = e.target.closest && e.target.closest("a[href]");
    if (a && !a.closest("#reader")) stop();
  }, true);

  if (synth) synth.onvoiceschanged = () => {};

  /* ---------- reading time (for Reading goals) ----------
   * Counts time only while a reading is on screen, the tab is visible, and the
   * student did something in the last 60 seconds (or read-aloud is playing).
   * Reports every ~30 seconds; the server caps each report and only keeps it
   * for signed-in students.
   */
  let lastActive = Date.now();
  let pending = 0;
  ["mousemove", "keydown", "scroll", "click", "touchstart", "wheel"].forEach((ev) =>
    document.addEventListener(ev, () => { lastActive = Date.now(); }, { passive: true, capture: true })
  );
  function localDay() {
    const d = new Date();
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }
  function flushReading() {
    if (pending > 0 && document.getElementById("reading-beat")) {
      setProps("reading-beat", { data: { day: localDay(), seconds: pending, t: Date.now() } });
      pending = 0;
    }
  }
  setInterval(() => {
    const el = reader();
    const reading = el && el.querySelector(".w");
    const active = Date.now() - lastActive < 60000 || speaking;
    if (reading && document.visibilityState === "visible" && active) {
      pending += 5;
      if (pending >= 30) flushReading();
    }
  }, 5000);
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") flushReading(); });
  document.addEventListener("click", (e) => {
    const a = e.target.closest && e.target.closest("a[href]");
    if (a && !a.closest("#reader")) flushReading();
  }, true);
})();
