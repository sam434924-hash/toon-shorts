// Safely set text content using textContent from JSON payload (never innerHTML or string eval)
(function applySafeTextPayload() {
  const payloadEl = document.getElementById("wb-safe-text-payload");
  if (!payloadEl) return;
  try {
    const data = JSON.parse(payloadEl.textContent || "{}");
    const titleEl = document.getElementById("wb-title");
    if (titleEl && typeof data.title === "string") {
      titleEl.textContent = data.title;
    }
    if (Array.isArray(data.cards)) {
      data.cards.forEach(c => {
        const cardEl = document.getElementById(c.id);
        if (cardEl) {
          const textEl = cardEl.querySelector(".word-text");
          if (textEl && typeof c.text === "string") {
            textEl.textContent = c.text;
          }
        }
      });
    }
  } catch (err) {
    console.warn("Could not apply safe text content:", err);
  }

  // Initialize board objects DOM structure from safe payload
  if (typeof window.initBoardObjects === "function") {
    window.initBoardObjects();
  }
})();

// Main Orchestrator and Deterministic Seek Engine
window.seekAnimation = function(ms) {
  if (!window.__boardObjectsInitialized && typeof window.initBoardObjects === "function") {
    window.initBoardObjects();
    window.__boardObjectsInitialized = true;
  }

  if ((!window.__annotationDrawers || window.__annotationDrawers.length === 0) && typeof window.initRoughSketches === "function") {
    const roughSvg = document.getElementById("rough-canvas");
    if (roughSvg && !roughSvg.firstChild) {
      window.initRoughSketches();
    }
  }

  if (window.__timeline) {
    window.__timeline.seek(ms);
  }

  const fps = window.__fps || 24;
  const frameIdx = Math.floor((ms / 1000.0) * fps);

  // 1-4. Character animation, mouth sync, idle life & FK limb poses
  if (typeof seekLimbAnimation === "function") {
    seekLimbAnimation(ms, frameIdx);
  }

  // 0. Compute deterministic multiplane camera state & parallax shifts
  if (typeof computeCameraState === "function" && typeof applyMultiplaneParallax === "function") {
    const camState = computeCameraState(ms, frameIdx);
    applyMultiplaneParallax(camState);
  }

  // 5. Progressive stroke-by-stroke drawing synced to speech
  if (window.__annotationDrawers) {
    window.__annotationDrawers.forEach(drawer => {
      const s = drawer.start_ms;
      const d = drawer.duration_ms;

      if (ms < s) {
        drawer.node.style.opacity = "0";
        drawer.paths.forEach(p => p.el.style.strokeDashoffset = String(p.len));
      } else if (ms >= s + d) {
        drawer.node.style.opacity = "1";
        drawer.paths.forEach(p => p.el.style.strokeDashoffset = "0");
      } else {
        const pVal = (ms - s) / d;
        drawer.node.style.opacity = "1";
        if (drawer.type === "arrow") {
          const shaftNodes = drawer.node.querySelectorAll(".arrow-shaft path");
          const headNodes = drawer.node.querySelectorAll(".arrow-head path");
          const pShaft = Math.min(1, pVal / 0.60);
          const pHead = Math.max(0, (pVal - 0.60) / 0.40);
          shaftNodes.forEach(p => {
            const len = parseFloat(p.style.strokeDasharray) || 50;
            p.style.strokeDashoffset = String(len * (1 - pShaft));
          });
          headNodes.forEach(p => {
            const len = parseFloat(p.style.strokeDasharray) || 50;
            p.style.strokeDashoffset = String(len * (1 - pHead));
          });
        } else {
          drawer.paths.forEach(item => {
            item.el.style.strokeDashoffset = String(item.len * (1 - pVal));
          });
        }
      }
    });
  }

  // 6. Highlight item currently being spoken
  if (window.__cardTimings && window.__cardTimings.length > 0) {
    window.__cardTimings.forEach(timing => {
      const cardEl = document.getElementById(timing.id);
      const isSpoken = (ms >= timing.start_ms && ms < timing.end_ms);
      if (cardEl) {
        if (isSpoken) {
          cardEl.classList.add("active-speaking");
        } else {
          cardEl.classList.remove("active-speaking");
        }
      }
    });
  }

  // 7. Progressive animation for stage visuals (template-based)
  if (typeof window.updateStageVisuals === "function") {
    window.updateStageVisuals(ms);
  }

  // 7b. Pure deterministic animation for board objects (Phase 4B-4)
  if (typeof window.updateBoardObjects === "function") {
    window.updateBoardObjects(ms);
  }

  // 8. Deterministic night studio background motion (LED pulse, glow particles, twinkling windows)
  if (typeof window.updateNightStudioEffects === "function") {
    window.updateNightStudioEffects(ms);
  }

  // 9. Interactive Speech Bubble (Phase 5)
  if (typeof window.updateSpeechBubble === "function") {
    window.updateSpeechBubble(ms);
  }
};

window.seekTo = window.seekAnimation;

// Verification function to ensure all modules loaded correctly
window.__checkModulesLoaded = function() {
  const missing = [];
  if (typeof initRoughSketches !== "function") missing.push("rough_draw (initRoughSketches)");
  if (typeof computeCameraState !== "function") missing.push("camera_engine (computeCameraState)");
  if (typeof applyMultiplaneParallax !== "function") missing.push("camera_engine (applyMultiplaneParallax)");
  if (typeof seekLimbAnimation !== "function") missing.push("gestures_fk (seekLimbAnimation)");
  if (typeof window.updateStageVisuals !== "function") missing.push("stage_visuals (updateStageVisuals)");
  if (typeof window.updateNightStudioEffects !== "function") missing.push("stage_visuals (updateNightStudioEffects)");
  if (typeof window.seekTo !== "function") missing.push("main (seekTo)");
  return missing;
};
