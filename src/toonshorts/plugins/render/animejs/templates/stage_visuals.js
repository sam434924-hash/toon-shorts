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
        const len = pEl.getTotalLength() || 60;
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
        const len = pEl.getTotalLength() || 320;
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
        const l1 = stroke1.getTotalLength() || 40;
        stroke1.style.strokeDashoffset = String(l1 * (1 - p1));
      }
      if (stroke2) {
        const l2 = stroke2.getTotalLength() || 40;
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
