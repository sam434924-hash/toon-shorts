// Deterministic update of stage visuals at timestamp ms
window.updateStageVisuals = function(ms) {
  if (!window.__stageVisuals || window.__stageVisuals.length === 0) return;

  window.__stageVisuals.forEach(vis => {
    const el = document.getElementById(vis.dom_id);
    if (!el) return;

    if (ms < vis.start_ms) {
      el.style.opacity = "0";
      const packetEl = document.getElementById(vis.dom_id + "-packet");
      if (packetEl) packetEl.style.opacity = "0";
      return;
    }

    el.style.opacity = "1";
    const p = Math.min(1.0, Math.max(0.0, (ms - vis.start_ms) / vis.duration_ms));

    if (vis.type === "flow") {
      const pArrow = Math.min(1.0, p / 0.7);
      const arrowPaths = el.querySelectorAll(".flow-arrow-svg path");
      arrowPaths.forEach(pEl => {
        let len = 60;
        try { if (typeof pEl.getTotalLength === 'function') len = pEl.getTotalLength() || 60; } catch (e) {}
        pEl.style.strokeDashoffset = String(len * (1 - pArrow));
      });
      const nodeBadges = el.querySelectorAll(".flow-node-badge");
      nodeBadges.forEach((badge, nIdx) => {
        const bob = Math.sin((ms - vis.start_ms) * 0.003 + nIdx * 1.5) * 3;
        badge.style.transform = `translateY(${bob}px)`;
      });
    } else if (vis.type === "request_response") {
      const arrowPaths = el.querySelectorAll(".rr-arrow-svg path");
      arrowPaths.forEach(pEl => {
        let len = 320;
        try { if (typeof pEl.getTotalLength === 'function') len = pEl.getTotalLength() || 320; } catch (e) {}
        pEl.style.strokeDashoffset = String(len * (1 - Math.min(1.0, p / 0.5)));
      });
      const boxBob = Math.sin((ms - vis.start_ms) * 0.003) * 2;
      const cIcon = el.querySelector(".rr-client .rr-box-icon");
      const sIcon = el.querySelector(".rr-server .rr-box-icon");
      if (cIcon) cIcon.style.transform = `translateY(${boxBob}px)`;
      if (sIcon) sIcon.style.transform = `translateY(${-boxBob}px)`;

      const packetEl = document.getElementById(vis.dom_id + "-packet");
      if (packetEl) {
        if (p < 0.15) {
          packetEl.style.opacity = "0";
        } else if (p >= 0.15 && p < 0.55) {
          packetEl.style.opacity = "1";
          const t = (p - 0.15) / 0.40;
          const eased = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
          const px = 20 + eased * 270;
          const py = 6 + Math.sin((ms - vis.start_ms) * 0.015) * 3;
          packetEl.style.transform = `translate(${px}px, ${py}px)`;
        } else if (p >= 0.55 && p < 0.65) {
          packetEl.style.opacity = "1";
          const py = 6 + Math.sin((ms - vis.start_ms) * 0.015) * 3;
          packetEl.style.transform = `translate(290px, ${py}px)`;
        } else if (p >= 0.65 && p <= 1.0) {
          packetEl.style.opacity = "1";
          const t = (p - 0.65) / 0.35;
          const eased = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
          const px = 290 - eased * 270;
          const py = 58 + Math.sin((ms - vis.start_ms) * 0.015) * 3;
          packetEl.style.transform = `translate(${px}px, ${py}px)`;
        }
      }
    } else if (vis.type === "typed_code") {
      const codeEl = document.getElementById(vis.dom_id + "-code");
      const cursorEl = document.getElementById(vis.dom_id + "-cursor");
      const full = vis.full_text || "";
      const charCount = Math.floor(p * full.length);
      if (codeEl) codeEl.textContent = full.substring(0, charCount);
      const blink = (ms % 600) < 300;
      if (cursorEl) cursorEl.style.opacity = blink ? "1" : "0";
    } else if (vis.type === "step_ladder") {
      const stepEls = el.querySelectorAll(".ladder-step");
      const count = stepEls.length || 1;
      stepEls.forEach((sEl, sIdx) => {
        const sStart = sIdx * (1.0 / count);
        if (p >= sStart) {
          sEl.style.opacity = "1";
          const sP = Math.min(1.0, (p - sStart) / (1.0 / count));
          sEl.style.transform = `translateX(${(1 - sP) * -30}px)`;
          const badge = sEl.querySelector(".ladder-num-badge");
          if (badge) {
            const bob = Math.sin((ms - vis.start_ms) * 0.003 + sIdx) * 3;
            badge.style.transform = `translateY(${bob}px)`;
          }
        } else {
          sEl.style.opacity = "0";
        }
      });
    } else if (vis.type === "check_cross") {
      const stroke1 = el.querySelector(".cc-stroke-1");
      const stroke2 = el.querySelector(".cc-stroke-2");
      const p1 = Math.min(1.0, p / 0.5);
      const p2 = Math.max(0.0, (p - 0.5) / 0.5);
      if (stroke1) {
        let l1 = 40;
        try { if (typeof stroke1.getTotalLength === 'function') l1 = stroke1.getTotalLength() || 40; } catch (e) {}
        stroke1.style.strokeDashoffset = String(l1 * (1 - p1));
      }
      if (stroke2) {
        let l2 = 40;
        try { if (typeof stroke2.getTotalLength === 'function') l2 = stroke2.getTotalLength() || 40; } catch (e) {}
        stroke2.style.strokeDashoffset = String(l2 * (1 - p2));
      }
      const iconBadge = el.querySelector(".cc-icon-badge");
      if (iconBadge) {
        const bob = Math.sin((ms - vis.start_ms) * 0.003) * 3;
        iconBadge.style.transform = `translateY(${bob}px)`;
      }
    } else if (vis.type === "counter") {
      const valEl = document.getElementById(vis.dom_id + "-val");
      const badge = document.getElementById(vis.dom_id + "-badge");
      const eased = 1 - Math.pow(1 - p, 3);
      const cur = Math.round(vis.from_val + eased * (vis.to_val - vis.from_val));
      if (valEl) valEl.textContent = (vis.prefix || "") + cur + (vis.suffix || "");
      if (badge) {
        const bob = Math.sin((ms - vis.start_ms) * 0.003) * 3;
        badge.style.transform = `translateY(${bob}px)`;
      }
    }
  });
};

// Deterministic Night Studio Background Motion
window.updateNightStudioEffects = function(ms) {
  const sec = ms / 1000.0;
  const frame = Math.floor((ms * (window.__fps || 24)) / 1000.0);

  // A. LED Glow Pulse (calm sine cycle ~2.5s)
  const pulseVal = 0.85 + 0.15 * Math.sin(sec * 2.5);
  const purpleLed = document.querySelector(".led-strip-purple");
  const blueLed = document.querySelector(".led-strip-blue");
  if (purpleLed) {
    purpleLed.style.boxShadow = `0 0 ${20 * pulseVal}px #a855f7, 0 0 ${45 * pulseVal}px #9333ea`;
    purpleLed.style.opacity = String(0.85 + 0.15 * pulseVal);
  }
  if (blueLed) {
    blueLed.style.boxShadow = `0 0 ${20 * pulseVal}px #0284c7, 0 0 ${45 * pulseVal}px #0369a1`;
    blueLed.style.opacity = String(0.85 + 0.15 * pulseVal);
  }

  // B. Twinkling City Windows (calm deterministic sine pattern)
  const winEls = document.querySelectorAll(".city-win");
  winEls.forEach((win, idx) => {
    const twinkle = 0.4 + 0.6 * Math.sin(sec * 1.8 + idx * 1.2);
    win.style.opacity = String(Math.max(0.15, twinkle));
  });

  // C. Drifting Glow Particles on Canvas (deterministic from frame)
  const pCanvas = document.getElementById("particles-canvas");
  if (pCanvas && pCanvas.getContext) {
    const ctx = pCanvas.getContext("2d");
    ctx.clearRect(0, 0, pCanvas.width, pCanvas.height);

    // 12 gentle floating particles
    const particleCount = 12;
    for (let i = 0; i < particleCount; i++) {
      const baseSeed = i * 73.13;
      const speed = 25 + (i % 5) * 8;
      // Deterministic cycle
      const y = (pCanvas.height - ((sec * speed + baseSeed * 10) % pCanvas.height));
      const x = (baseSeed * 17 + Math.sin(sec * 0.8 + i) * 35) % pCanvas.width;
      const alpha = 0.15 + 0.20 * Math.sin(sec * 1.5 + i);
      const rad = 2 + (i % 3);

      ctx.beginPath();
      ctx.arc(x, y, rad, 0, Math.PI * 2);
      ctx.fillStyle = (i % 2 === 0) ? `rgba(56, 189, 248, ${alpha})` : `rgba(192, 132, 252, ${alpha})`;
      ctx.shadowBlur = 8;
      ctx.shadowColor = (i % 2 === 0) ? "#38bdf8" : "#c084fc";
      ctx.fill();
    }
  }

  // D. Stage Visual Graphics Plugins deterministic seeker
  if (window.__stageVisuals) {
    window.__stageVisuals.forEach(v => {
      const el = document.querySelector(v.target);
      if (!el) return;

      const sMs = v.start_ms || 0;
      const dMs = v.duration_ms || 600;

      // Board item lifetime: at most 3 items on the board at once; clear old items with quick fade
      if (ms < sMs) {
        el.style.opacity = "0";
        el.style.display = "none";
        return;
      }
      el.style.display = "flex";

      const elapsed = ms - sMs;
      const progress = Math.min(1.0, elapsed / dMs);

      // Fade-out logic after hold time (hold ~5s or until end)
      const holdTime = 5500;
      if (elapsed > holdTime) {
        const fadeProgress = Math.min(1.0, (elapsed - holdTime) / 400.0);
        el.style.opacity = String(1.0 - fadeProgress);
      } else {
        el.style.opacity = "1";
      }

      // 1. Kinetic words: pop with spring overshoot (0 -> 1.18 -> 1.0) or slide
      if (v.type === "kinetic_words") {
        if (v.animation === "pop") {
          const scale = progress < 0.65 ? (progress / 0.65) * 1.18 : 1.18 - ((progress - 0.65) / 0.35) * 0.18;
          el.style.transform = `scale(${Math.max(0, scale)})`;
        } else {
          const slideY = (1.0 - progress) * 30;
          el.style.transform = `translateY(${slideY}px)`;
        }
      }

      // 2. Draw SVG: stroke-dashoffset animation
      if (v.type === "draw_svg") {
        const paths = el.querySelectorAll(".draw-path");
        paths.forEach(p => {
          const dashLen = 1200;
          p.style.strokeDashoffset = String(dashLen * (1.0 - progress));
        });

        // If arm numbers badge exists (octopus_vector)
        if (v.show_numbers) {
          const numStart = v.numbers_start_ms || (sMs + 600);
          const badges = el.querySelectorAll(".arm-num-badge");
          badges.forEach((b, bIdx) => {
            const bStart = numStart + bIdx * 80;
            if (ms >= bStart) {
              const bProg = Math.min(1.0, (ms - bStart) / 250);
              const bScale = bProg < 0.65 ? (bProg / 0.65) * 1.18 : 1.18 - ((bProg - 0.65) / 0.35) * 0.18;
              b.style.opacity = "1";
              b.style.transformOrigin = `${b.querySelector("circle").getAttribute("cx")}px ${b.querySelector("circle").getAttribute("cy")}px`;
              b.style.transform = `scale(${bScale})`;
            } else {
              b.style.opacity = "0";
            }
          });
        }
      }

      // 3. Hearts pop: Spring bounce pop-in with overshoot (0 -> 1.18 -> 1.0)
      if (v.type === "hearts_pop") {
        const items = el.querySelectorAll(".heart-item");
        items.forEach((item, hIdx) => {
          const hStart = sMs + hIdx * (v.stagger_ms || 240);
          if (ms >= hStart) {
            const hProg = Math.min(1.0, (ms - hStart) / 450);
            const spring = hProg < 0.65 ? (hProg / 0.65) * 1.18 : 1.18 - ((hProg - 0.65) / 0.35) * 0.18;
            item.style.opacity = "1";
            item.style.transform = `scale(${Math.max(0, spring)})`;
          } else {
            item.style.opacity = "0";
            item.style.transform = "scale(0)";
          }
        });
      }

      // 4. Blue blood drop: falls, glows, and springs (0 -> 1.18 -> 1.0)
      if (v.type === "blue_blood_drop") {
        const bProg = Math.min(1.0, elapsed / 450);
        const fallY = (1.0 - Math.min(1.0, bProg * 1.4)) * -40.0;
        const spring = bProg < 0.65 ? (bProg / 0.65) * 1.18 : 1.18 - ((bProg - 0.65) / 0.35) * 0.18;
        el.style.opacity = String(Math.min(1.0, bProg * 2.5));
        el.style.transform = `translateY(${fallY.toFixed(2)}px) scale(${Math.max(0, spring)})`;
      }
    });
  }
};

// Phase 4B-4: Board Objects & Animated Text DOM Initializer
window.initBoardObjects = function() {
  if (window.__enableBoardObjects === false) return;

  let objects = window.__boardObjects;
  if (!objects || objects.length === 0) {
    const payloadEl = document.getElementById("board-objects-payload");
    if (payloadEl && payloadEl.textContent) {
      try {
        objects = JSON.parse(payloadEl.textContent);
      } catch (e) {
        console.warn("Could not parse board-objects-payload JSON:", e);
        objects = [];
      }
    }
  }

  if (!Array.isArray(objects) || objects.length === 0) return;
  window.__resolvedBoardObjects = objects;

  function createSvgEl(tag, attrs) {
    const sEl = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const k in attrs) {
      sEl.setAttribute(k, attrs[k]);
    }
    return sEl;
  }

  objects.forEach(obj => {
    const rawSlot = String(obj.board_slot || "slot_mid").toLowerCase().trim();
    const slotSuffix = rawSlot.replace(/^slot_/, "");
    let slotEl = document.getElementById("board-slot-" + slotSuffix) ||
                 document.getElementById("board-slot-" + rawSlot) ||
                 document.getElementById("board-slot-" + (slotSuffix === "hero" ? "center" : (slotSuffix === "card" ? "mid" : "center")));
    if (!slotEl) slotEl = document.getElementById("board-objects-container");
    if (!slotEl) return;

    if (document.getElementById(obj.id)) return;

    const el = document.createElement("div");
    el.id = obj.id;
    el.className = "board-object bo-" + obj.type.replace(/_/g, "-");
    el.style.opacity = "0";
    el.style.boxSizing = "border-box";
    el.style.maxWidth = "87%";
    el.style.maxHeight = "87%";
    el.style.transformOrigin = "50% 50%";

    // Handle declared overlap {badge or label on a card corner} with layer order
    if (obj.overlap || obj.declared_overlap) {
      const ov = obj.overlap || obj.declared_overlap;
      el.classList.add("bo-declared-overlap");
      el.style.position = "absolute";
      el.style.zIndex = String(ov.layer_order || ov.layer || 2);
      const corner = ov.corner || "top_right";
      if (corner === "top_right") {
        el.style.top = "8px";
        el.style.right = "8px";
      } else if (corner === "top_left") {
        el.style.top = "8px";
        el.style.left = "8px";
      } else if (corner === "bottom_right") {
        el.style.bottom = "8px";
        el.style.right = "8px";
      } else if (corner === "bottom_left") {
        el.style.bottom = "8px";
        el.style.left = "8px";
      }
    }

    const st = obj.style || {};
    const pal = st.palette || ["#1b1516", "#ffffff", "#38bdf8", "#818cf8"];
    const outlineCol = st.outline_color || "#1b1516";
    const highlightCol = st.highlight_color || "#38bdf8";
    const fontFam = st.font_family || "Arial, sans-serif";

    if (obj.type === "text_pop") {
      const textSpan = document.createElement("div");
      textSpan.className = "bo-text-pop";
      textSpan.style.fontFamily = fontFam;
      textSpan.style.fontSize = (obj.data.font_size || 36) + "px";
      textSpan.style.color = pal[0] || outlineCol;
      textSpan.style.border = "3px solid " + outlineCol;
      textSpan.style.background = pal[1] || "#ffffff";
      textSpan.textContent = obj.data.text || "";
      el.appendChild(textSpan);

    } else if (obj.type === "text_typewriter") {
      const preEl = document.createElement("div");
      preEl.className = "bo-typewriter";
      preEl.style.fontFamily = "'Consolas', monospace";
      const codeSpan = document.createElement("span");
      codeSpan.id = obj.id + "-body";
      codeSpan.textContent = "";
      const cursorSpan = document.createElement("span");
      cursorSpan.id = obj.id + "-cursor";
      cursorSpan.className = "bo-cursor";
      cursorSpan.textContent = "|";
      preEl.appendChild(codeSpan);
      preEl.appendChild(cursorSpan);
      el.appendChild(preEl);

    } else if (obj.type === "highlight_word") {
      const hWrap = document.createElement("div");
      hWrap.className = "bo-highlight-word";
      hWrap.style.fontFamily = fontFam;

      const fullTxt = obj.data.text || "";
      const targetW = (obj.data.target_word || "").toLowerCase();
      const words = fullTxt.split(/\s+/);

      words.forEach((w, wIdx) => {
        const cleanW = w.toLowerCase().replace(/[^a-z0-9]/g, "");
        const span = document.createElement("span");
        span.textContent = w + (wIdx < words.length - 1 ? " " : "");
        if (targetW && (cleanW === targetW || targetW.includes(cleanW) || cleanW.includes(targetW))) {
          span.className = "bo-highlight-target";
          span.id = obj.id + "-target-word";
          span.style.color = highlightCol;
          span.style.borderBottom = "4px solid " + highlightCol;
        }
        hWrap.appendChild(span);
      });
      el.appendChild(hWrap);

    } else if (obj.type === "diagram_flow") {
      const diagWrap = document.createElement("div");
      diagWrap.className = "bo-diagram-flow";
      const nodes = (obj.data.nodes || []).slice(0, 6);

      nodes.forEach((nodeText, nIdx) => {
        const nodeEl = document.createElement("div");
        nodeEl.id = obj.id + "-node-" + nIdx;
        nodeEl.className = "bo-diagram-node";
        nodeEl.style.borderColor = pal[nIdx % pal.length] || outlineCol;
        nodeEl.style.color = pal[0] || outlineCol;
        nodeEl.textContent = nodeText;
        diagWrap.appendChild(nodeEl);

        if (nIdx < nodes.length - 1) {
          const arrowEl = document.createElement("div");
          arrowEl.id = obj.id + "-arrow-" + nIdx;
          arrowEl.className = "bo-diagram-arrow";
          const svgEl = createSvgEl("svg", { viewBox: "0 0 60 24", width: "60", height: "24" });
          const shaft = createSvgEl("path", {
            class: "flow-arrow-shaft",
            d: "M 4 12 L 48 12",
            stroke: highlightCol,
            "stroke-width": "4",
            "stroke-linecap": "round"
          });
          const head = createSvgEl("path", {
            class: "flow-arrow-head",
            d: "M 42 6 L 54 12 L 42 18",
            fill: "none",
            stroke: highlightCol,
            "stroke-width": "4",
            "stroke-linecap": "round",
            "stroke-linejoin": "round"
          });
          svgEl.appendChild(shaft);
          svgEl.appendChild(head);
          arrowEl.appendChild(svgEl);
          diagWrap.appendChild(arrowEl);
        }
      });
      el.appendChild(diagWrap);

    } else if (obj.type === "svg_draw") {
      const svgWrap = document.createElement("div");
      svgWrap.className = "bo-svg-draw";
      const sType = obj.data.svg_type || "vector";
      const svgCol = highlightCol || outlineCol;

      if (sType === "check") {
        const svgEl = createSvgEl("svg", { viewBox: "0 0 100 100", width: "120", height: "120" });
        const checkPath = createSvgEl("path", {
          class: "draw-path",
          d: "M 20 52 L 42 74 L 82 26",
          stroke: svgCol,
          "stroke-width": "8",
          "stroke-linecap": "round",
          "stroke-linejoin": "round",
          fill: "none",
          style: "stroke-dasharray: 140; stroke-dashoffset: 140;"
        });
        svgEl.appendChild(checkPath);
        svgWrap.appendChild(svgEl);
      } else {
        const svgEl = createSvgEl("svg", { viewBox: "0 0 200 120", width: "220", height: "130" });
        const rectPath = createSvgEl("rect", {
          class: "draw-path",
          x: "10",
          y: "10",
          width: "180",
          height: "100",
          rx: "14",
          stroke: svgCol,
          "stroke-width": "6",
          fill: "none",
          style: "stroke-dasharray: 600; stroke-dashoffset: 600;"
        });
        svgEl.appendChild(rectPath);
        svgWrap.appendChild(svgEl);
      }

      if (obj.data.label) {
        const lbl = document.createElement("div");
        lbl.className = "bo-svg-label";
        lbl.style.fontFamily = fontFam;
        lbl.style.fontSize = "24px";
        lbl.style.fontWeight = "700";
        lbl.style.color = pal[0] || outlineCol;
        lbl.style.marginTop = "8px";
        lbl.textContent = obj.data.label;
        svgWrap.appendChild(lbl);
      }
      el.appendChild(svgWrap);

    } else if (obj.type === "icon_pop") {
      const iconWrap = document.createElement("div");
      iconWrap.className = "bo-icon-pop";
      const cnt = Math.min(5, Math.max(1, obj.data.count || 3));
      const iconType = obj.data.icon || "heart";

      for (let i = 0; i < cnt; i++) {
        const itemEl = document.createElement("div");
        itemEl.id = obj.id + "-icon-" + i;
        itemEl.className = "bo-icon-item";
        itemEl.style.opacity = "0";
        itemEl.style.transform = "scale(0)";

        const svgEl = createSvgEl("svg", { viewBox: "0 0 100 100", width: "80", height: "80" });
        if (iconType === "heart") {
          const pth = createSvgEl("path", {
            d: "M 50,28 C 50,15 35,5 20,5 C 8,5 0,16 0,30 C 0,55 35,75 50,92 C 65,75 100,55 100,30 C 100,16 92,5 80,5 C 65,5 50,15 50,28 Z",
            fill: pal[2] || "#ef4444"
          });
          svgEl.appendChild(pth);
        } else {
          const pth = createSvgEl("path", {
            d: "M 50 15 C 50 15 25 50 25 68 C 25 82 36 92 50 92 C 64 92 75 82 75 68 C 75 50 50 15 50 15 Z",
            fill: highlightCol || "#38bdf8"
          });
          svgEl.appendChild(pth);
        }
        itemEl.appendChild(svgEl);
        iconWrap.appendChild(itemEl);
      }
      el.appendChild(iconWrap);
    } else if (obj.type === "image") {
      const imgWrap = document.createElement("div");
      imgWrap.id = obj.id + "-container";
      imgWrap.className = "bo-image bo-image-" + (obj.data.preset || "slide_in_tilt").replace(/_/g, "-");
      imgWrap.style.width = "100%";
      imgWrap.style.display = "flex";
      imgWrap.style.justifyContent = "center";
      imgWrap.style.alignItems = "center";
      imgWrap.style.position = "relative";

      const imgEl = document.createElement("img");
      imgEl.src = obj.data.image_url || "";
      imgEl.alt = obj.data.alt || "";
      imgEl.style.maxWidth = "80%";
      imgEl.style.maxHeight = "360px";
      imgEl.style.objectFit = "contain";
      imgEl.style.borderRadius = "8px";
      imgWrap.appendChild(imgEl);

      if (obj.data.preset === "detail_highlight") {
        const svgHl = createSvgEl("svg", {
          viewBox: "0 0 100 100",
          style: "position: absolute; width: 120px; height: 120px; pointer-events: none;",
          id: obj.id + "-hl-svg"
        });
        const hx = (obj.data.highlight_region && obj.data.highlight_region[0]) || 50;
        const hy = (obj.data.highlight_region && obj.data.highlight_region[1]) || 50;
        const hlCircle = createSvgEl("circle", {
          cx: "50",
          cy: "50",
          r: "35",
          stroke: highlightCol || "#38bdf8",
          "stroke-width": "6",
          fill: "none",
          class: "draw-path",
          style: "stroke-dasharray: 240; stroke-dashoffset: 240;"
        });
        svgHl.appendChild(hlCircle);
        svgHl.style.left = "calc(" + hx + "% - 60px)";
        svgHl.style.top = "calc(" + hy + "% - 60px)";
        imgWrap.appendChild(svgHl);
      }

      el.appendChild(imgWrap);

    } else if (obj.type === "custom") {
      const customWrap = document.createElement("div");
      customWrap.className = "bo-custom bo-custom-level-" + ((obj.data && obj.data.level) || 1);
      customWrap.id = obj.id + "-container";
      customWrap.style.width = "100%";
      customWrap.style.display = "flex";
      customWrap.style.justifyContent = "center";
      customWrap.style.alignItems = "center";
      customWrap.style.position = "relative";

      const sLevel = (obj.data && obj.data.level) || 1;
      if (obj.data && obj.data.svg) {
        let cleanSvg = obj.data.svg;
        if (cleanSvg.search(/<\s*\/?\s*ns\d+:/i) !== -1) {
          cleanSvg = cleanSvg.replace(/<\s*(\/)?\s*ns\d+:/gi, '<$1').replace(/\s+xmlns:ns\d+="[^"]*"/gi, '');
        }
        customWrap.innerHTML = cleanSvg;
        const svgEl = customWrap.querySelector("svg");
        if (svgEl) {
          svgEl.style.maxWidth = "100%";
          svgEl.style.maxHeight = "400px";
          svgEl.style.display = "block";
          const preset = (obj.data && obj.data.motion_preset ? obj.data.motion_preset : "draw_on").toLowerCase();
          if (preset === "draw_on") {
            const paths = svgEl.querySelectorAll("path, line, polyline, polygon, rect, circle, ellipse");
            paths.forEach((pEl) => {
              let len = 100;
              try {
                if (typeof pEl.getTotalLength === "function") {
                  len = Math.max(1, pEl.getTotalLength());
                }
              } catch (e) {}
              pEl.style.strokeDasharray = String(len);
              pEl.style.strokeDashoffset = String(len);
            });
          }
        }
      }

      if (sLevel === 2 && obj.data && obj.data.js_code) {
        try {
          window.__level2Effects = window.__level2Effects || {};
          const factory = new Function("anime", "seed", "el", "return (" + obj.data.js_code + ")");
          const effectFn = factory(window.anime, obj.seed, customWrap);
          window.__level2Effects[obj.id] = effectFn;
        } catch (err) {
          console.error("Failed to initialize Level 2 effect for " + obj.id, err);
        }
      }
      el.appendChild(customWrap);
    }

    slotEl.appendChild(el);
  });
};

// Pure deterministic seek update for board objects
window.updateBoardObjects = function(ms) {
  if (window.__enableBoardObjects === false) return;
  const objects = window.__resolvedBoardObjects;
  if (!objects || objects.length === 0) return;

  objects.forEach(obj => {
    const el = document.getElementById(obj.id);
    if (!el) return;

    if (ms < obj.start_ms || ms > obj.exit_ms) {
      el.style.opacity = "0";
      el.style.display = "none";
      return;
    }

    el.style.display = "flex";
    const elapsed = ms - obj.start_ms;
    const dur = obj.duration_ms || 600;
    const p = Math.min(1.0, Math.max(0.0, elapsed / dur));

    // Exit fade (300ms window before exit_ms)
    let pExit = 1.0;
    if (ms > obj.exit_ms - 300) {
      pExit = Math.max(0.0, (obj.exit_ms - ms) / 300.0);
    }

    // Enter styling: pop, slide_in, draw_on
    if (obj.type === "custom") {
      el.style.transform = "none";
      el.style.opacity = String(pExit.toFixed(3));
    } else if (obj.enter === "pop") {
      const spring = p < 0.7 ? (p / 0.7) * 1.14 : 1.14 - ((p - 0.7) / 0.3) * 0.14;
      el.style.transform = "scale(" + Math.max(0, spring).toFixed(3) + ")";
      el.style.opacity = String(pExit.toFixed(3));
    } else if (obj.enter === "slide_in") {
      const slideY = (1.0 - p) * -15.0;
      el.style.transform = "translateY(" + slideY.toFixed(2) + "px)";
      el.style.opacity = String((Math.min(1.0, p * 2.0) * pExit).toFixed(3));
    } else {
      el.style.transform = "none";
      el.style.opacity = String(pExit.toFixed(3));
    }

    // Type-specific progressive animation as pure function of time
    if (obj.type === "text_typewriter") {
      const bodyEl = document.getElementById(obj.id + "-body");
      const cursorEl = document.getElementById(obj.id + "-cursor");
      const fullText = (obj.data && obj.data.text) ? obj.data.text : "";
      const pType = Math.min(1.0, elapsed / (dur * 0.75));
      const chars = Math.floor(pType * fullText.length);
      if (bodyEl) bodyEl.textContent = fullText.substring(0, chars);
      if (cursorEl) cursorEl.style.opacity = (ms % 500) < 250 ? "1" : "0";

    } else if (obj.type === "highlight_word") {
      const targetEl = document.getElementById(obj.id + "-target-word");
      if (targetEl) {
        if (p >= 0.60) {
          const pSub = Math.min(1.0, (p - 0.60) / 0.40);
          const bounce = pSub < 0.5 ? 1.0 + pSub * 0.3 : 1.15 - (pSub - 0.5) * 0.3;
          targetEl.style.transform = "scale(" + bounce.toFixed(3) + ")";
          targetEl.style.display = "inline-block";
        } else {
          targetEl.style.transform = "none";
        }
      }

    } else if (obj.type === "diagram_flow") {
      const nodes = (obj.data && obj.data.nodes) ? obj.data.nodes : [];
      const stages = Math.max(1, nodes.length * 2 - 1);
      nodes.forEach((_, nIdx) => {
        const nodeEl = document.getElementById(obj.id + "-node-" + nIdx);
        const stageThreshold = (2 * nIdx) / stages;
        if (p >= stageThreshold) {
          const pNode = Math.min(1.0, (p - stageThreshold) * stages);
          const spring = pNode < 0.65 ? (pNode / 0.65) * 1.15 : 1.15 - ((pNode - 0.65) / 0.35) * 0.15;
          if (nodeEl) {
            nodeEl.style.opacity = "1";
            nodeEl.style.transform = "scale(" + Math.max(0, spring).toFixed(3) + ")";
          }
        } else if (nodeEl) {
          nodeEl.style.opacity = "0";
          nodeEl.style.transform = "scale(0)";
        }

        if (nIdx < nodes.length - 1) {
          const arrEl = document.getElementById(obj.id + "-arrow-" + nIdx);
          const arrThreshold = (2 * nIdx + 1) / stages;
          if (arrEl) {
            if (p >= arrThreshold) {
              const pArr = Math.min(1.0, (p - arrThreshold) * stages);
              arrEl.style.opacity = "1";
              const paths = arrEl.querySelectorAll("path");
              paths.forEach(pth => {
                const len = 50;
                pth.style.strokeDasharray = String(len);
                pth.style.strokeDashoffset = String((len * (1 - pArr)).toFixed(2));
              });
            } else {
              arrEl.style.opacity = "0";
            }
          }
        }
      });

    } else if (obj.type === "svg_draw") {
      const paths = el.querySelectorAll(".draw-path");
      paths.forEach(pth => {
        const len = pth.tagName.toLowerCase() === "rect" ? 600 : 140;
        pth.style.strokeDashoffset = String((len * (1 - p)).toFixed(2));
      });

    } else if (obj.type === "icon_pop") {
      const cnt = Math.min(5, Math.max(1, (obj.data && obj.data.count) || 3));
      for (let i = 0; i < cnt; i++) {
        const itemEl = document.getElementById(obj.id + "-icon-" + i);
        if (!itemEl) continue;
        const tIcon = obj.start_ms + i * 160;
        if (ms >= tIcon) {
          const pIcon = Math.min(1.0, (ms - tIcon) / 350.0);
          const spring = pIcon < 0.65 ? (pIcon / 0.65) * 1.18 : 1.18 - ((pIcon - 0.65) / 0.35) * 0.18;
          itemEl.style.opacity = "1";
          itemEl.style.transform = "scale(" + Math.max(0, spring).toFixed(3) + ")";
        } else {
          itemEl.style.opacity = "0";
          itemEl.style.transform = "scale(0)";
        }
      }
    } else if (obj.type === "image") {
      const imgWrap = document.getElementById(obj.id + "-container");
      if (!imgWrap) return;
      const preset = (obj.data && obj.data.preset) || "slide_in_tilt";

      if (preset === "slide_in_tilt") {
        const ty = (1.0 - p) * 60;
        const tilt = (1.0 - p) * -8;
        imgWrap.style.transform = "translateY(" + ty.toFixed(2) + "px) rotate(" + tilt.toFixed(2) + "deg)";
        imgWrap.style.opacity = String(p.toFixed(3));
      } else if (preset === "paper_tear_reveal") {
        const clipProg = (p * 100).toFixed(1);
        imgWrap.style.clipPath = "polygon(0 0, " + clipProg + "% 0, " + clipProg + "% 100%, 0 100%)";
        imgWrap.style.opacity = "1";
      } else if (preset === "detail_highlight") {
        imgWrap.style.opacity = p > 0.05 ? "1" : "0";
        const hlCircle = el.querySelector("#" + obj.id + "-hl-svg circle");
        if (hlCircle) {
          const hlProg = Math.max(0, Math.min(1.0, (p - 0.2) / 0.8));
          hlCircle.style.strokeDashoffset = String((240 * (1 - hlProg)).toFixed(2));
        }
      } else if (preset === "stamp_slam") {
        const scale = p < 0.6 ? 2.0 - (p / 0.6) * 1.05 : 0.95 + ((p - 0.6) / 0.4) * 0.05;
        imgWrap.style.transform = "scale(" + Math.max(0, scale).toFixed(3) + ")";
        imgWrap.style.opacity = p > 0.05 ? "1" : "0";
      } else if (preset === "push_in") {
        const scale = 1.0 + p * 0.25;
        imgWrap.style.transform = "scale(" + scale.toFixed(3) + ")";
        imgWrap.style.opacity = "1";
      } else if (preset === "travel") {
        const tx = (p - 0.5) * 260;
        const hop = -Math.abs(Math.sin(p * Math.PI * 5)) * 18;
        const shadowBlur = (10 + Math.abs(hop) * 0.4).toFixed(1);
        const shadowOffset = (14 - hop * 0.3).toFixed(1);
        imgWrap.style.transform = "translateX(" + tx.toFixed(2) + "px) translateY(" + hop.toFixed(2) + "px)";
        imgWrap.style.filter = "drop-shadow(0px " + shadowOffset + "px " + shadowBlur + "px rgba(0,0,0,0.45))";
        imgWrap.style.opacity = p > 0.03 ? (p < 0.95 ? "1" : String(((1 - p) / 0.05).toFixed(2))) : String((p / 0.03).toFixed(2));
      } else if (preset === "pop_with_wobble" || preset === "pop-with-wobble") {
        const enterScale = p < 0.25 ? (p / 0.25) * 1.15 : 1.0 + 0.15 * Math.exp(-(p - 0.25) * 6);
        const wobble = Math.sin((p - 0.1) * Math.PI * 8) * Math.exp(-p * 4) * 12;
        imgWrap.style.transform = "scale(" + Math.max(0, enterScale).toFixed(3) + ") rotate(" + wobble.toFixed(2) + "deg)";
        imgWrap.style.opacity = p > 0.03 ? "1" : String((p / 0.03).toFixed(2));
      }

    } else if (obj.type === "custom") {
      const customWrap = document.getElementById(obj.id + "-container");
      if (!customWrap) return;
      const sLevel = (obj.data && obj.data.level) || 1;

      if (sLevel === 1) {
        const preset = (obj.data && obj.data.motion_preset ? obj.data.motion_preset : "draw_on").toLowerCase();
        if (preset === "draw_on") {
          const svgEl = customWrap.querySelector("svg");
          if (svgEl) {
            const paths = svgEl.querySelectorAll("path, line, polyline, polygon, rect, circle, ellipse");
            paths.forEach(pEl => {
              try {
                if (typeof pEl.getTotalLength === "function") {
                  const len = Math.max(1, pEl.getTotalLength());
                  pEl.style.strokeDashoffset = String((len * (1 - p)).toFixed(2));
                }
              } catch (e) {}
            });
          }
          customWrap.style.opacity = p > 0.05 ? "1" : String((p * 20).toFixed(2));
        } else if (preset === "fade_in") {
          customWrap.style.opacity = String(p.toFixed(3));
        } else if (preset === "pop" || preset === "bounce") {
          const scale = p < 0.7 ? (p / 0.7) * 1.14 : 1.14 - ((p - 0.7) / 0.3) * 0.14;
          customWrap.style.transform = "scale(" + Math.max(0, scale).toFixed(3) + ")";
          customWrap.style.opacity = p > 0.05 ? "1" : String((p * 20).toFixed(2));
        } else if (preset === "slide_in") {
          const ty = (1.0 - p) * 50;
          customWrap.style.transform = "translateY(" + ty.toFixed(2) + "px)";
          customWrap.style.opacity = String(p.toFixed(3));
        } else if (preset === "pulse") {
          const s = 1.0 + 0.08 * Math.sin(p * Math.PI * 4);
          customWrap.style.transform = "scale(" + s.toFixed(3) + ")";
          customWrap.style.opacity = "1";
        } else if (preset === "spin" || preset === "rotate") {
          customWrap.style.transform = "rotate(" + (p * 360).toFixed(1) + "deg)";
          customWrap.style.opacity = "1";
        }

        const tl = obj.data && obj.data.timeline;
        if (Array.isArray(tl) && tl.length > 0) {
          for (let k = 0; k < tl.length; k++) {
            const kf = tl[k];
            if (typeof kf.at === "number" && p >= kf.at) {
              if (kf.opacity !== undefined) customWrap.style.opacity = String(kf.opacity);
              if (kf.scale !== undefined) customWrap.style.transform = "scale(" + kf.scale + ")";
              if (kf.rotate !== undefined) customWrap.style.transform = "rotate(" + kf.rotate + "deg)";
              if (kf.translateY !== undefined) customWrap.style.transform = "translateY(" + kf.translateY + "px)";
            }
          }
        }

        // Storyboard specific kinetic diagram animations (Phase 3)
        if (obj.id === "bo_sc3_nodes") {
          const svgEl = customWrap.querySelector("svg");
          if (svgEl) {
            const nPlan = svgEl.querySelector(".node-plan, g:nth-of-type(1)");
            const arr1 = svgEl.querySelector(".arrow-1, g:nth-of-type(2)");
            const nAct = svgEl.querySelector(".node-act, g:nth-of-type(3)");
            const arr2 = svgEl.querySelector(".arrow-2, g:nth-of-type(4)");
            const nCheck = svgEl.querySelector(".node-check, g:nth-of-type(5)");
            const arr3 = svgEl.querySelector(".arrow-3, g:nth-of-type(6)");
            const nAdjust = svgEl.querySelector(".node-adjust, g:nth-of-type(7)");
            const arrLoop = svgEl.querySelector(".arrow-loop");
            const dot = svgEl.querySelector(".glowing-dot");

            const setNodeState = (el, tTrigger) => {
              if (!el) return;
              if (elapsed >= tTrigger) {
                const pN = Math.min(1.0, (elapsed - tTrigger) / 350.0);
                const s = pN < 0.65 ? (pN / 0.65) * 1.15 : 1.15 - ((pN - 0.65) / 0.35) * 0.15;
                el.style.opacity = "1";
                el.style.transform = "scale(" + Math.max(0, s).toFixed(3) + ")";
                el.style.transformOrigin = "center";
              } else {
                el.style.opacity = "0";
                el.style.transform = "scale(0)";
              }
            };

            setNodeState(nPlan, 0);
            if (arr1) arr1.style.opacity = elapsed >= 350 ? "1" : "0";
            setNodeState(nAct, 500);
            if (arr2) arr2.style.opacity = elapsed >= 850 ? "1" : "0";
            setNodeState(nCheck, 1000);
            if (arr3) arr3.style.opacity = elapsed >= 1350 ? "1" : "0";
            setNodeState(nAdjust, 1500);
            if (arrLoop) arrLoop.style.opacity = elapsed >= 1800 ? "1" : "0";

            // Glowing dot travelling along the nodes and loop back
            if (dot) {
              const loopDur = 2800.0;
              const tProg = (elapsed % loopDur) / loopDur;
              let cx = 77, cy = 52;
              if (tProg < 0.25) {
                const u = tProg / 0.25;
                cx = 77 + u * (257 - 77);
                cy = 52;
              } else if (tProg < 0.50) {
                const u = (tProg - 0.25) / 0.25;
                cx = 257 + u * (437 - 257);
                cy = 52;
              } else if (tProg < 0.75) {
                const u = (tProg - 0.50) / 0.25;
                cx = 437 + u * (617 - 437);
                cy = 52;
              } else {
                const u = (tProg - 0.75) / 0.25;
                cx = 617 - u * (617 - 77);
                cy = 52 + Math.sin(u * Math.PI) * 60;
              }
              dot.setAttribute("cx", cx.toFixed(1));
              dot.setAttribute("cy", cy.toFixed(1));
              dot.style.opacity = elapsed >= 200 ? "1" : "0";
            }
          }
        } else if (obj.id === "bo_sc4_cards") {
          const svgEl = customWrap.querySelector("svg");
          if (svgEl) {
            const cards = svgEl.querySelectorAll("g");
            cards.forEach((card, cIdx) => {
              const tCard = cIdx * 350;
              if (elapsed >= tCard) {
                const pC = Math.min(1.0, (elapsed - tCard) / 380.0);
                if (cIdx < 3) {
                  const tx = (1.0 - pC) * -65;
                  card.style.transform = "translateX(" + tx.toFixed(1) + "px)";
                  card.style.opacity = String(pC.toFixed(3));
                } else {
                  // Final report snaps into place
                  const snap = pC < 0.65 ? (pC / 0.65) * 1.22 : 1.22 - ((pC - 0.65) / 0.35) * 0.22;
                  card.style.transform = "scale(" + Math.max(0, snap).toFixed(3) + ")";
                  card.style.opacity = String(pC.toFixed(3));
                  card.style.transformOrigin = "595px 65px";
                }
              } else {
                card.style.opacity = "0";
              }
            });
          }
        } else if (obj.id === "bo_sc5_warn") {
          if (elapsed < 1400) {
            const flash = Math.sin((elapsed / 1400) * Math.PI * 6) > 0;
            customWrap.style.transform = flash ? "scale(1.04)" : "scale(1.0)";
          }
        } else if (obj.id === "bo_sc5_shield") {
          const svgEl = customWrap.querySelector("svg");
          if (svgEl) {
            const cursor = svgEl.querySelector(".file-cursor");
            const barrier = svgEl.querySelector(".stop-barrier");
            const shield = svgEl.querySelector(".safety-shield");
            if (cursor) {
              const pCursor = Math.min(1.0, elapsed / 850.0);
              const curX = 20 + pCursor * 160;
              cursor.style.transform = "translateX(" + curX.toFixed(1) + "px)";
              cursor.style.opacity = "1";
            }
            if (barrier) {
              barrier.style.opacity = elapsed >= 800 ? "1" : "0";
            }
            if (shield) {
              if (elapsed >= 800) {
                const pS = Math.min(1.0, (elapsed - 800) / 600.0);
                const sScale = pS < 0.65 ? (pS / 0.65) * 1.15 : 1.15 - ((pS - 0.65) / 0.35) * 0.15;
                shield.style.transform = "scale(" + Math.max(0, sScale).toFixed(3) + ")";
                shield.style.opacity = "1";
                shield.style.transformOrigin = "505px 65px";
              } else {
                shield.style.opacity = "0";
              }
            }
          }
        } else if (obj.id === "bo_sc6_pillars") {
          const svgEl = customWrap.querySelector("svg");
          if (svgEl) {
            const pThink = svgEl.querySelector(".pillar-think");
            const arr1 = svgEl.querySelector(".arrow-p1");
            const pAct = svgEl.querySelector(".pillar-act");
            const arr2 = svgEl.querySelector(".arrow-p2");
            const pVerify = svgEl.querySelector(".pillar-verify");

            const popWord = (el, tTrigger) => {
              if (!el) return;
              if (elapsed >= tTrigger) {
                const pW = Math.min(1.0, (elapsed - tTrigger) / 400.0);
                const s = pW < 0.65 ? (pW / 0.65) * 1.18 : 1.18 - ((pW - 0.65) / 0.35) * 0.18;
                el.style.opacity = "1";
                el.style.transform = "scale(" + Math.max(0, s).toFixed(3) + ")";
                el.style.transformOrigin = "center";
              } else {
                el.style.opacity = "0";
                el.style.transform = "scale(0)";
              }
            };

            popWord(pThink, 0);
            if (arr1) arr1.style.opacity = elapsed >= 350 ? "1" : "0";
            popWord(pAct, 550);
            if (arr2) arr2.style.opacity = elapsed >= 900 ? "1" : "0";
            popWord(pVerify, 1100);
          }
        }
      } else if (sLevel === 2) {
        if (window.__level2Effects && typeof window.__level2Effects[obj.id] === "function") {
          try {
            const ret = window.__level2Effects[obj.id](p, obj.seed, customWrap);
            if (ret && typeof ret === "object") {
              if (ret.rotate !== undefined) customWrap.style.transform = "rotate(" + ret.rotate + "deg)";
              if (ret.scale !== undefined) customWrap.style.transform = "scale(" + ret.scale + ")";
              if (ret.opacity !== undefined) customWrap.style.opacity = String(ret.opacity);
            }
          } catch (err) {
            console.error("Level 2 effect error for " + obj.id + " at t=" + p, err);
          }
        }
      }
    }
  });
};
