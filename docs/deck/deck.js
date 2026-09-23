// Deck runtime: picks the variant, mounts each demo slot as a recording or a
// live terminal, and hands the "next" key to a paused recording before
// reveal.js sees it. Plain ES2017, no build step, works from file://.
(function () {
  "use strict";

  var params = new URLSearchParams(window.location.search);
  var VARIANTS = {
    talk: { label: "Talk", totalTime: 40 * 60 },
    lightning: { label: "Lightning", totalTime: 5 * 60 }
  };
  var variant = params.get("v") || "talk";
  if (!VARIANTS[variant]) variant = "talk";
  var liveMode = params.get("demo") === "live";
  var autoMode = params.get("auto") === "1";

  // A live terminal that does not answer within this window falls back to
  // the recording, so a dead ttyd never stalls the talk.
  var LIVE_PROBE_MS = 2500;
  var AUTO_SLIDE_MS = 12000;
  var NEXT_KEYS = ["ArrowRight", "ArrowDown", "PageDown", " ", "n", "N"];
  var TOGGLE_KEYS = ["l", "L"];

  // ---------- variant filter ----------

  document.querySelectorAll("[data-variants]").forEach(function (el) {
    var wanted = el.getAttribute("data-variants").split(/\s+/);
    if (wanted.indexOf(variant) === -1) el.remove();
  });
  document.documentElement.setAttribute("data-variant", variant);
  document.title = document.title + " · " + VARIANTS[variant].label;

  // ---------- demo slots ----------

  var slots = new Map();

  function castSource(name) {
    var casts = window.DECK_CASTS || {};
    return casts[name] !== undefined ? { data: casts[name] } : { url: "casts/" + name + ".cast" };
  }

  function reset(el) {
    var old = slots.get(el);
    if (old && old.player) old.player.dispose();
    slots.delete(el);
    el.textContent = "";
  }

  function addBadge(el, text, kind) {
    var badge = document.createElement("span");
    badge.className = "term-badge" + (kind ? " " + kind : "");
    badge.textContent = text;
    el.appendChild(badge);
  }

  function mountRecorded(el, fallbackNote) {
    reset(el);
    var state = { kind: "recorded", player: null, playing: false, ended: false };
    state.player = AsciinemaPlayer.create(castSource(el.dataset.cast), el, {
      theme: "deck",
      fit: "both",
      idleTimeLimit: 2,
      pauseOnMarkers: !autoMode,
      speed: parseFloat(el.dataset.speed || "1"),
      terminalLineHeight: 1.2,
      controls: "auto"
    });
    state.player.addEventListener("play", function () {
      state.playing = true;
      state.ended = false;
    });
    state.player.addEventListener("pause", function () {
      state.playing = false;
    });
    state.player.addEventListener("ended", function () {
      state.playing = false;
      state.ended = true;
      if (autoMode) Reveal.next();
    });
    addBadge(el, fallbackNote || "recorded", fallbackNote ? "fallback" : "");
    slots.set(el, state);
    return state;
  }

  function probe(url) {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, LIVE_PROBE_MS);
    return fetch(url, { mode: "no-cors", signal: controller.signal })
      .then(function () { return true; }, function () { return false; })
      .finally(function () { clearTimeout(timer); });
  }

  function mountLive(el) {
    reset(el);
    slots.set(el, { kind: "probing" });
    return probe(el.dataset.live).then(function (reachable) {
      if (!reachable) return mountRecorded(el, "live unreachable · recording");
      reset(el);
      var frame = document.createElement("iframe");
      frame.src = el.dataset.live;
      frame.title = "Live terminal";
      el.appendChild(frame);
      addBadge(el, "live", "live");
      var state = { kind: "live" };
      slots.set(el, state);
      return state;
    });
  }

  function mount(el, live) {
    return live && el.dataset.live ? mountLive(el) : Promise.resolve(mountRecorded(el));
  }

  function slotsOf(slide) {
    return slide ? Array.prototype.slice.call(slide.querySelectorAll(".term[data-cast]")) : [];
  }

  function currentState() {
    var el = slotsOf(Reveal.getCurrentSlide())[0];
    return el ? slots.get(el) : undefined;
  }

  function enter(slide) {
    slotsOf(slide).forEach(function (el) {
      var ready = slots.has(el) ? Promise.resolve(slots.get(el)) : mount(el, liveMode);
      ready.then(function (state) {
        if (autoMode && state && state.kind === "recorded") state.player.play();
      });
    });
  }

  function leave(slide) {
    slotsOf(slide).forEach(function (el) {
      var state = slots.get(el);
      if (state && state.kind === "recorded" && state.playing) state.player.pause();
    });
  }

  function toggleLive() {
    var el = slotsOf(Reveal.getCurrentSlide())[0];
    if (!el || !el.dataset.live) return;
    var state = slots.get(el);
    mount(el, !(state && state.kind === "live"));
  }

  // Capture phase: runs before reveal.js's own key handler. While a recording
  // has frames left, "next" plays it (or skips to its next marker); once it
  // ends, "next" advances the slide as usual.
  window.addEventListener("keydown", function (event) {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    if (TOGGLE_KEYS.indexOf(event.key) !== -1) {
      toggleLive();
      event.stopImmediatePropagation();
      return;
    }
    if (NEXT_KEYS.indexOf(event.key) === -1) return;
    var state = currentState();
    if (!state || state.kind !== "recorded" || state.ended) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (state.playing) state.player.seek({ marker: "next" });
    else state.player.play();
  }, true);

  // ---------- reveal.js ----------

  Reveal.initialize({
    hash: true,
    width: 1280,
    height: 720,
    margin: 0.06,
    center: false,
    controls: true,
    progress: true,
    slideNumber: "c/t",
    transition: "fade",
    transitionSpeed: "fast",
    backgroundTransition: "none",
    totalTime: VARIANTS[variant].totalTime,
    autoSlide: autoMode ? AUTO_SLIDE_MS : 0,
    loop: autoMode,
    plugins: [RevealNotes]
  }).then(function () {
    enter(Reveal.getCurrentSlide());
  });

  Reveal.on("slidechanged", function (event) {
    leave(event.previousSlide);
    enter(event.currentSlide);
  });
})();
