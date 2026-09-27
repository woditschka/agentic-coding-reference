// Deck runtime: picks the variant, mounts each demo slot as a recording, and
// hands the "next" key to a paused recording before reveal.js sees it. Plain ES2017, no build step, works from file://.
(function () {
  "use strict";

  var params = new URLSearchParams(window.location.search);
  var VARIANTS = {
    talk: { label: "Talk", totalTime: 40 * 60 },
    lightning: { label: "Lightning", totalTime: 5 * 60 }
  };
  var variant = params.get("v") || "talk";
  if (!VARIANTS[variant]) variant = "talk";
  var autoMode = params.get("auto") === "1";

  var AUTO_SLIDE_MS = 12000;
  var NEXT_KEYS = ["ArrowRight", "ArrowDown", "PageDown", " ", "n", "N"];

  // ---------- variant filter ----------

  document.querySelectorAll("[data-variants]").forEach(function (el) {
    var wanted = el.getAttribute("data-variants").split(/\s+/);
    if (wanted.indexOf(variant) === -1) el.remove();
  });
  document.documentElement.setAttribute("data-variant", variant);
  document.title = document.title + " · " + VARIANTS[variant].label;

  // Unattended mode advances on a timer, one fragment per tick. A slide
  // with fragments gets a shorter tick so its reveals stay watchable, never
  // under AUTO_STEP_MIN_MS. A demo slide gets no timer: it waits for its
  // recording to end, which advances it (see mountRecorded).
  var AUTO_STEP_MIN_MS = 3000;
  if (autoMode) {
    document.querySelectorAll(".slides section").forEach(function (slide) {
      if (slide.hasAttribute("data-autoslide")) return;
      if (slide.querySelector(".term[data-cast]")) {
        slide.setAttribute("data-autoslide", "0");
        return;
      }
      var steps = slide.querySelectorAll(".fragment").length;
      if (steps === 0) return;
      var tick = Math.max(AUTO_STEP_MIN_MS, Math.round((AUTO_SLIDE_MS * 2) / (steps + 1)));
      slide.setAttribute("data-autoslide", String(tick));
    });
  }

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

  function addBadge(el, text) {
    var badge = document.createElement("span");
    badge.className = "term-badge";
    badge.textContent = text;
    el.appendChild(badge);
  }

  function mountRecorded(el) {
    reset(el);
    var state = { player: null, playing: false, ended: false };
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
    addBadge(el, "recorded");
    slots.set(el, state);
    return state;
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
      var state = slots.has(el) ? slots.get(el) : mountRecorded(el);
      if (autoMode) state.player.play();
    });
  }

  // Leaving a slide tears its recording down, so the slide starts it from
  // the beginning when it is entered again.
  function leave(slide) {
    slotsOf(slide).forEach(reset);
  }

  // Capture phase: runs before reveal.js's own key handler. While a recording
  // has frames left, "next" plays it (or skips to its next marker); once it
  // ends, "next" advances the slide as usual. Shift with a next key advances
  // at once, pausing the recording, so a demo can be passed without playing;
  // the advance is explicit because reveal.js binds Shift with an arrow to the
  // last slide and Shift with Space to the previous one.
  window.addEventListener("keydown", function (event) {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    if (NEXT_KEYS.indexOf(event.key) === -1) return;
    var state = currentState();
    if (!state || state.ended) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (event.shiftKey) {
      if (state.playing) state.player.pause();
      Reveal.next();
      return;
    }
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
    // A stray key or click must not stop an unattended loop.
    autoSlideStoppable: !autoMode,
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
