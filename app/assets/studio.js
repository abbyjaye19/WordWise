/* WordWise Reading Studio — browser side.
 * Draws the reading into #reader (one <span class="w"> per word), and runs the
 * reading tools: read aloud with word highlighting, tap-a-word, highlighter,
 * reading ruler, and one-paragraph focus. Talks to Dash with set_props.
 */
(function () {
  "use strict";

  const WW = (window.WW = {});
  const state = {
    mode: "lookup", color: "gold", start: null, ruler: false, focus: false,
    doc: null,        // the reading (original wording)
    view: null,       // Reading Levels: {mode, title, count, covered, paras: [...]} or null for the original
    showOrig: false,  // show the original under each AI paragraph
    hlMap: {},        // saved highlights {wordIndex: color}; kept even when some words aren't on screen
    cur: null,        // read-aloud position {p, start} for replay / back / next
  };
  const RATES = ["0.7", "0.85", "1", "1.15", "1.3"];
  const RATE_LABELS = { "0.7": "Slower", "0.85": "Slow", "1": "Normal", "1.15": "Fast", "1.3": "Faster" };
  const READALONG = ["both", "sentence", "word"];
  const READALONG_LABELS = { both: "Both", sentence: "Sentence", word: "Word" };
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

  function logTool(tool) {
    if (document.getElementById("tool-beat")) setProps("tool-beat", { data: { tool: tool, t: Date.now() } });
  }

  /* ---------- render ---------- */
  function docKey(doc) {
    return doc.title + "|" + JSON.stringify(doc.sections).length + "|" + doc.sections.length;
  }

  function paraCount(doc) {
    return doc.sections.reduce((n, s) => n + s.paragraphs.length, 0);
  }

  function viewFits(doc, view) {
    return !!(doc && view && view.paras && view.title === doc.title && view.count === paraCount(doc));
  }

  // One <span class="w"> per word. data-o = offset in the paragraph (read-aloud); data-i = word number
  // in the original reading (highlights). AI-written words have no data-i, so they can't be highlighted.
  function wordsHtml(text, firstIndex) {
    let out = "";
    let last = 0;
    let wi = firstIndex;
    const re = /\S+/g;
    let m;
    while ((m = re.exec(text))) {
      out += esc(text.slice(last, m.index));
      const idx = wi === null ? "" : ` data-i="${wi++}"`;
      out += `<span class="w"${idx} data-o="${m.index}">${esc(m[0])}</span>`;
      last = m.index + m[0].length;
    }
    return { html: out + esc(text.slice(last)), next: wi };
  }

  const VIEW_NAMES = { simplified: "Simplified wording", detailed: "Detailed explanation" };

  function draw() {
    const el = reader();
    const doc = state.doc;
    if (!el || !doc) return;
    const view = viewFits(doc, state.view) ? state.view : null;
    const key = docKey(doc) + "|" + (view ? view.mode + view.level + view.covered : "original") + "|" + (view && state.showOrig ? 1 : 0);
    if (el.dataset.key === key && el.querySelector(".w")) {
      applyHighlights(state.hlMap);
      return;
    }
    stop();
    let html = "";
    if (view) {
      html += `<div class="r-ai-banner" role="note"><strong>AI · ${VIEW_NAMES[view.mode] || "AI version"}</strong>` +
        ` <span>Same meaning, written by AI. Switch to Original any time to check it.</span></div>`;
    }
    let pi = 0;
    let wi = 0;
    const many = doc.sections.length > 1;
    doc.sections.forEach((s, si) => {
      html += `<section class="r-section" data-s="${si}">`;
      if (many) html += `<h3 class="r-label">${esc(s.label)}</h3>`;
      s.paragraphs.forEach((p) => {
        const orig = wordsHtml(p, wi);
        wi = orig.next;
        if (view && pi < view.covered && view.paras[pi]) {
          html += `<div class="r-pair"><p class="r-p r-ai" data-p="${pi}">${wordsHtml(view.paras[pi], null).html}</p>`;
          if (state.showOrig) html += `<p class="r-orig" data-p="${pi}">${orig.html}</p>`;
          html += "</div>";
        } else {
          html += `<p class="r-p" data-p="${pi}">${orig.html}</p>`;
        }
        pi += 1;
      });
      html += "</section>";
    });
    if (view && view.covered < pi) {
      html += `<p class="r-ai-note">The AI version covers the first ${view.covered} paragraphs. The rest is in the original wording.</p>`;
    }
    el.innerHTML = html;
    el.dataset.key = key;
    el.dataset.view = view ? view.mode : "original";
    el.classList.toggle("focus-mode", state.focus);
    state.start = null;
    state.cur = null;
    applyHighlights(state.hlMap);
  }

  function syncViewButtons() {
    const mode = viewFits(state.doc, state.view) ? state.view.mode : "original";
    ["original", "simplified", "detailed"].forEach((m) => {
      const b = document.getElementById("view-" + m);
      if (b) b.setAttribute("aria-pressed", m === mode ? "true" : "false");
    });
    const so = document.getElementById("view-showorig");
    if (so) {
      so.hidden = mode === "original";
      so.setAttribute("aria-pressed", state.showOrig ? "true" : "false");
    }
  }

  WW.render = function (doc, view) {
    const el = reader();
    if (!el) return;
    state.view = view && view.paras ? view : null;
    if (!doc || !doc.sections) {
      stop();
      state.doc = null;
      state.view = null;
      state.hlMap = {};
      el.innerHTML = "";
      el.dataset.key = "";
      pushHighlights();
      syncViewButtons();
      return;
    }
    const same = state.doc && docKey(state.doc) === docKey(doc) && el.dataset.key && el.querySelector(".w");
    state.doc = doc;
    if (!same) state.hlMap = { ...(doc.highlights || {}) }; // same reading (saved, or view changed): keep current highlights
    if (!viewFits(doc, state.view)) state.view = null;
    draw();
    syncViewButtons();
  };

  /* ---------- highlights (saved with the reading, used by downloads) ---------- */
  const HL = ["hl-gold", "hl-green", "hl-blue"];

  function applyHighlights(map) {
    state.hlMap = { ...map };
    document.querySelectorAll("#reader .w[data-i]").forEach((w) => {
      w.classList.remove(...HL);
      const c = state.hlMap[w.dataset.i];
      if (c) w.classList.add("hl-" + c);
    });
    pushHighlights();
  }

  let pushTimer = null;
  function pushHighlights() {
    clearTimeout(pushTimer);
    pushTimer = setTimeout(() => {
      // Start from the saved map so words that aren't on screen (AI view) keep their highlights.
      const map = { ...state.hlMap };
      document.querySelectorAll("#reader .w[data-i]").forEach((w) => {
        delete map[w.dataset.i];
        if (w.classList.contains("hl-gold")) map[w.dataset.i] = "gold";
        else if (w.classList.contains("hl-green")) map[w.dataset.i] = "green";
        else if (w.classList.contains("hl-blue")) map[w.dataset.i] = "blue";
      });
      state.hlMap = map;
      setProps("highlights-store", { data: map });
    }, 150);
  }

  /* ---------- helpers ---------- */
  // Short forms a voice may misread, and that don't end a sentence (Prof. Whitfield, Rm. 114, e.g.).
  const ABBREV = {
    "prof.": "Professor", "dr.": "Doctor", "mr.": "Mister", "mrs.": "Missus", "ms.": "Miz", "rm.": "Room",
    "e.g.": "for example", "i.e.": "that is", "etc.": "et cetera", "vs.": "versus", "approx.": "approximately",
    "dept.": "Department", "ave.": "Avenue", "no.": "number", "pp.": "pages", "ch.": "chapter", "fig.": "figure",
  };
  const NO_BREAK = /(?:\b(?:prof|dr|mr|mrs|ms|rm|e\.g|i\.e|vs|approx|dept|ave|no|pp|ch|fig|st|jr|sr)\.|\b[A-Z]\.)\s*$/i;

  function sentences(text) {
    // [{start, end}] for each sentence in the text
    const out = [];
    const re = /[^.!?]+(?:[.!?]+["'”’)\]]*)?\s*/g;
    let m;
    while ((m = re.exec(text))) {
      if (!m[0]) break;
      const last = out[out.length - 1];
      // "Prof. Whitfield" is one sentence, not two.
      if (last && NO_BREAK.test(text.slice(last.start, last.end).trimEnd())) last.end = m.index + m[0].length;
      else out.push({ start: m.index, end: m.index + m[0].length });
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

  /* ---------- read aloud ----------
   * Uses the browser's own voices (free, no key). Edge's "Natural" voices sound the most human, so
   * they are ranked first. Voices load a moment after the page does, so we wait for them before the
   * first sentence instead of falling back to the robotic default voice.
   */
  let VOICES = [];
  const VOICE_KEY = "ww-voice";
  const GOOD_NAMES = /\b(ava|andrew|emma|brian|jenny|aria|guy|michelle|christopher|eric|steffan|libby|sonia|ryan|natasha|william)\b/i;

  function voiceScore(v) {
    let s = 0;
    if (/natural|neural|online/i.test(v.name)) s += 100;
    if (/google/i.test(v.name)) s += 60;
    if (GOOD_NAMES.test(v.name)) s += 20;
    if (/en[-_]US/i.test(v.lang)) s += 10;
    else if (/en[-_](GB|AU|CA|IE|NZ)/i.test(v.lang)) s += 5;
    if (/desktop|espeak/i.test(v.name)) s -= 50;
    return s;
  }

  function englishVoices() {
    return VOICES.filter((v) => /^en/i.test(v.lang)).sort((a, b) => voiceScore(b) - voiceScore(a));
  }

  function voiceLabel(v) {
    const m = v.name.match(/^(?:Microsoft|Google)\s+(.+?)(?:\s+Online)?(?:\s+\((Natural)\))?(?:\s+-\s+.*)?$/i);
    const name = m ? m[1] : v.name;
    const region = (v.lang.split(/[-_]/)[1] || "").toUpperCase();
    const natural = /natural|neural|online|google/i.test(v.name);
    return name + (region ? " (" + region + ")" : "") + (natural ? " · natural" : "");
  }

  function fillVoiceSelect() {
    const sel = document.getElementById("tts-voice");
    if (!sel) return;
    const list = englishVoices();
    const want = localStorage.getItem(VOICE_KEY);
    const key = list.map((v) => v.name).join("|") + "#" + want;
    if (sel.dataset.key === key) return;
    sel.dataset.key = key;
    sel.innerHTML = "";
    if (!list.length) {
      const o = document.createElement("option");
      o.value = "";
      o.textContent = "Default voice";
      sel.appendChild(o);
      return;
    }
    list.forEach((v, i) => {
      const o = document.createElement("option");
      o.value = v.name;
      o.textContent = (i === 0 ? "★ " : "") + voiceLabel(v);
      sel.appendChild(o);
    });
    sel.value = list.some((v) => v.name === want) ? want : list[0].name;
  }

  function loadVoices() {
    if (!synth) return;
    VOICES = synth.getVoices();
    fillVoiceSelect();
  }
  if (synth) {
    loadVoices();
    if (synth.addEventListener) synth.addEventListener("voiceschanged", loadVoices);
    else synth.onvoiceschanged = loadVoices;
  }

  // Wait (briefly) until the voice list is ready, so the first sentence uses a good voice.
  function withVoices(cb) {
    if (!synth || VOICES.length) return cb();
    let done = false;
    const go = () => {
      if (done) return;
      done = true;
      loadVoices();
      cb();
    };
    if (synth.addEventListener) synth.addEventListener("voiceschanged", go, { once: true });
    setTimeout(go, 1500);
  }

  function pickVoice() {
    if (!synth) return null;
    const list = englishVoices();
    const want = localStorage.getItem(VOICE_KEY);
    return list.find((v) => v.name === want) || list[0] || null;
  }

  // Speed and read-along style come from the Reading settings (saved preferences on <html>).
  function rateKey() {
    const r = document.documentElement.dataset.rate;
    return RATES.includes(r) ? r : "1";
  }
  function rate() {
    return parseFloat(rateKey());
  }

  function clearSpeaking() {
    document.querySelectorAll("#reader .w-speaking").forEach((w) => w.classList.remove("w-speaking"));
    document.querySelectorAll("#reader .s-speaking").forEach((w) => w.classList.remove("s-speaking"));
    document.querySelectorAll("#reader .r-reading").forEach((p) => p.classList.remove("r-reading"));
  }

  function markSentence(p, start, end) {
    document.querySelectorAll("#reader .s-speaking").forEach((w) => w.classList.remove("s-speaking"));
    p.querySelectorAll(".w").forEach((w) => {
      const o = +w.dataset.o;
      if (o >= start && o < end) w.classList.add("s-speaking");
    });
  }

  /* Pronunciation fixes from the Pronunciation Helper: {paragraph text: [{word, occurrence, say}]}.
   * Only the spoken text changes; the words on screen stay exactly as written. */
  state.fixes = {};
  WW.setFixes = function (fixes) {
    state.fixes = fixes || {};
  };

  function sayMap(p) {
    const fixes = (state.fixes[p.textContent] || []).map((x) => ({ ...x, key: bare(x.word).toLowerCase() }));
    const out = new Map();
    const seen = {};
    p.querySelectorAll(".w").forEach((w) => {
      const token = w.textContent;
      const b = bare(token).toLowerCase();
      if (!b) return;
      seen[b] = (seen[b] || 0) + 1;
      const abbr = ABBREV[token.replace(/^[^\p{L}]+|[,;:)"'”’]+$/gu, "").toLowerCase()];
      if (abbr) return out.set(w, { say: abbr, abbr: true }); // the fixed list wins: it also drops the period
      const f = fixes.find((x) => x.key === b && x.occurrence === seen[b]);
      if (f) out.set(w, f.say);
    });
    return out;
  }

  // The text actually spoken for [start, end) of a paragraph, plus where each word starts in it
  // (so the highlight still follows the right word when a respelling is a different length).
  function spokenText(p, start, end, says) {
    const text = p.textContent;
    let spoken = "";
    let prev = start;
    const marks = [];
    p.querySelectorAll(".w").forEach((w) => {
      const o = +w.dataset.o;
      if (o < start || o >= end) return;
      spoken += text.slice(prev, o);
      marks.push({ s: spoken.length, w: w });
      const token = w.textContent;
      const say = says.get(w);
      const b = bare(token);
      if (say && say.abbr) spoken += token.replace(/[\p{L}.]+/u, say.say); // "Prof." -> "Professor" (no sentence-ending pause)
      else spoken += say && b ? token.replace(b, say) : token;
      prev = o + token.length;
    });
    spoken += text.slice(prev, end);
    return { spoken: spoken, marks: marks };
  }

  // Group whole sentences into chunks of up to ~240 characters: fewer gaps between sentences than
  // speaking one sentence at a time, and short enough for every browser's voices.
  function chunksFrom(text, startAt) {
    const ss = sentences(text).filter((c) => c.end > startAt);
    if (ss.length) ss[0] = { start: Math.max(ss[0].start, startAt), end: ss[0].end };
    const out = [];
    ss.forEach((s) => {
      const last = out[out.length - 1];
      if (last && s.end - last.start <= 240) {
        last.end = s.end;
        last.sents.push(s);
      } else {
        out.push({ start: s.start, end: s.end, sents: [s] });
      }
    });
    return out;
  }

  function speakFrom(pEl, offset) {
    if (!synth) {
      alert("Read aloud isn't available in this browser. Try Edge or Chrome.");
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
      const says = sayMap(p);
      const chunks = chunksFrom(p.textContent, startAt);
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
        let sentence = c.sents[0];
        state.cur = { p: p, start: sentence.start };
        markSentence(p, sentence.start, sentence.end);
        const sp = spokenText(p, c.start, c.end, says);
        const u = new SpeechSynthesisUtterance(sp.spoken);
        const v = pickVoice();
        if (v) {
          u.voice = v;
          u.lang = v.lang;
        }
        u.rate = rate();
        u.onboundary = (ev) => {
          if (myRun !== run || (ev.name && ev.name !== "word")) return;
          let m = null;
          for (const x of sp.marks) {
            if (x.s <= ev.charIndex) m = x;
            else break;
          }
          if (!m) return;
          const w = m.w;
          p.querySelectorAll(".w-speaking").forEach((x) => x.classList.remove("w-speaking"));
          w.classList.add("w-speaking");
          const o = +w.dataset.o;
          if (o >= sentence.end || o < sentence.start) {
            const s = c.sents.find((x) => o >= x.start && o < x.end);
            if (s) {
              sentence = s;
              state.cur = { p: p, start: s.start };
              markSentence(p, s.start, s.end);
            }
          }
          if (state.ruler) moveRulerTo(w);
        };
        u.onend = next;
        u.onerror = (ev) => {
          if (myRun === run && ev.error !== "interrupted" && ev.error !== "canceled") next();
        };
        synth.speak(u);
      };
      next();
    };
    withVoices(() => speakPara(pEl, offset));
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
    const wp = w && w.closest(".r-p");
    logTool("read_aloud");
    if (wp) speakFrom(wp, +w.dataset.o);
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
    if (synth) {
      if (paused) synth.resume(); // some browsers stay paused after cancel() otherwise
      synth.cancel();
    }
    speaking = false;
    paused = false;
    clearSpeaking();
    updateButtons();
    const r = document.getElementById("ww-ruler");
    if (r) r.hidden = true;
  }

  // Replay the current sentence, or jump one sentence back / forward.
  function jump(step) {
    const all = paras();
    if (!all.length) return;
    const cur = state.cur && document.body.contains(state.cur.p) ? state.cur : null;
    if (!cur) return speakFrom(all[0], 0);
    const ss = sentences(cur.p.textContent);
    let i = ss.findIndex((x) => cur.start >= x.start && cur.start < x.end);
    if (i < 0) i = 0;
    let pi = all.indexOf(cur.p);
    i += step;
    if (i < 0) {
      if (pi === 0) i = 0;
      else { pi -= 1; i = sentences(all[pi].textContent).length - 1; }
    } else if (i >= ss.length) {
      if (pi >= all.length - 1) return stop();
      pi += 1; i = 0;
    }
    const target = all[pi];
    speakFrom(target, sentences(target.textContent)[i].start);
  }

  function changeRate(step) {
    const i = Math.max(0, Math.min(RATES.length - 1, RATES.indexOf(rateKey()) + step));
    setProps("pref-rate", { value: RATES[i] }); // saved like any other reading setting
    document.documentElement.dataset.rate = RATES[i];
    updateButtons();
  }

  function cycleReadalong() {
    const now = document.documentElement.dataset.readalong || "both";
    const next = READALONG[(READALONG.indexOf(now) + 1) % READALONG.length];
    setProps("pref-readalong", { value: next });
    document.documentElement.dataset.readalong = next;
    updateButtons();
  }

  // A new speed only applies to new speech, so restart the current sentence at the new speed.
  new MutationObserver(() => {
    updateButtons();
    if (speaking && !paused && state.cur && document.body.contains(state.cur.p)) speakFrom(state.cur.p, state.cur.start);
  }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-rate"] });
  new MutationObserver(updateButtons).observe(document.documentElement, { attributes: true, attributeFilter: ["data-readalong"] });

  function sayText(text) {
    if (!synth || !text) return;
    stop();
    withVoices(() => {
      const u = new SpeechSynthesisUtterance(text);
      const v = pickVoice();
      if (v) {
        u.voice = v;
        u.lang = v.lang;
      }
      u.rate = rate();
      synth.speak(u);
    });
  }

  // Choosing a voice: remember it on this device and play a short sample.
  document.addEventListener("change", (e) => {
    if (!e.target || e.target.id !== "tts-voice") return;
    localStorage.setItem(VOICE_KEY, e.target.value);
    sayText("Hi! This is how I sound when I read to you.");
  });

  function updateButtons() {
    const playBtn = document.getElementById("tts-play");
    if (playBtn) playBtn.textContent = paused ? "▶ Resume" : "▶ Read aloud";
    const pauseBtn = document.getElementById("tts-pause");
    if (pauseBtn) pauseBtn.setAttribute("aria-pressed", paused ? "true" : "false");
    const speed = document.getElementById("tts-speed-label");
    if (speed) speed.textContent = RATE_LABELS[rateKey()] + " · " + rateKey() + "×";
    const slower = document.getElementById("tts-slower");
    if (slower) slower.disabled = rateKey() === RATES[0];
    const faster = document.getElementById("tts-faster");
    if (faster) faster.disabled = rateKey() === RATES[RATES.length - 1];
    const ra = document.getElementById("tts-readalong");
    if (ra) ra.textContent = "Highlight: " + (READALONG_LABELS[document.documentElement.dataset.readalong] || READALONG_LABELS.both);
  }
  WW.refreshTools = function () { updateButtons(); syncViewButtons(); fillVoiceSelect(); };

  /* ---------- word actions ---------- */
  function lookup(w) {
    const word = bare(w.textContent);
    if (!word) return;
    document.querySelectorAll("#reader .w-active").forEach((x) => x.classList.remove("w-active"));
    w.classList.add("w-active");
    const p = w.closest(".r-p, .r-orig");
    if (p.classList.contains("r-p")) setCurrent(p);
    setProps("word-request", { data: { word: word, sentence: sentenceAround(p, +w.dataset.o), t: Date.now() } });
  }

  let hlLogged = false;
  function highlight(w, forceOn) {
    if (w.dataset.i === undefined) return; // AI-written words: highlights belong to the original text
    if (!hlLogged) { hlLogged = true; logTool("highlighter"); }
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
    if (state[key]) logTool(key);
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
      else if (state.mode === "read") {
        const p = w.closest(".r-p");
        if (p) speakFrom(p, +w.dataset.o);
        else { const pair = w.closest(".r-pair"); if (pair) speakFrom(pair.querySelector(".r-p"), 0); }
      } else lookup(w);
      return;
    }
    const btn = t.closest && t.closest("button");
    if (!btn) return;
    switch (btn.id) {
      case "tts-play": return play();
      case "tts-pause": return paused ? play() : pause();
      case "tts-stop": return stop();
      case "tts-replay": logTool("replay"); return jump(0);
      case "tts-back": logTool("replay"); return jump(-1);
      case "tts-next": return jump(1);
      case "tts-slower": return changeRate(-1);
      case "tts-faster": return changeRate(1);
      case "tts-readalong": return cycleReadalong();
      case "view-showorig":
        state.showOrig = !state.showOrig;
        draw();
        syncViewButtons();
        return;
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
    if (!sel.toString().trim().includes(" ")) return;
    // Use whole words, even if the drag started or ended in the middle of one ("he exam" -> "The exam").
    const words = Array.from(el.querySelectorAll(".w")).filter((w) => range.intersectsNode(w));
    const text = words.map((w) => w.textContent).join(" ").replace(/\s+/g, " ").trim();
    if (!text || !text.includes(" ")) return;
    if (state.mode === "highlight") {
      el.querySelectorAll(".w[data-i]").forEach((w) => {
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
      const title = state.doc ? state.doc.title : "";
      setProps("reading-beat", { data: { day: localDay(), seconds: pending, title: title, t: Date.now() } });
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
