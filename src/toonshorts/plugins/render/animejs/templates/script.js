// Store stroke drawing items for progressive animated line drawing
window.__annotationDrawers = [];

// Initialize Rough.js Sketch Drawings with Fixed Deterministic Seeds
function initRoughSketches() {
  const roughSvg = document.getElementById("rough-canvas");
  const wbEl = document.querySelector(".whiteboard-outer");
  if (!roughSvg || !wbEl || typeof rough === "undefined") return;

  const rc = rough.svg(roughSvg);
  const canvasRect = roughSvg.getBoundingClientRect();

  // 1. Hand-sketched underline under the title badge (fixed seed: 101)
  const titleEl = document.getElementById("wb-title");
  if (titleEl) {
    const tRect = titleEl.getBoundingClientRect();
    const leftX = (tRect.left - canvasRect.left) + 16;
    const rightX = (tRect.right - canvasRect.left) - 16;
    const underY = (tRect.bottom - canvasRect.top) + 8;
    const uLine = rc.line(leftX, underY, rightX, underY, {
      seed: 101,
      stroke: '#f59e0b',
      strokeWidth: 5.5,
      roughness: 1.3,
      bowing: 1.2
    });
    uLine.id = 'rough-title-underline';
    roughSvg.appendChild(uLine);
  }

  // 2. Hand-sketched circles around keyword text (NOT list numbers)
  const cards = document.querySelectorAll(".word-card");
  const cardRects = [];

  cards.forEach((card, idx) => {
    const textEl = card.querySelector(".word-text") || card.querySelector(".word-text-wrapper") || card;
    const numEl = card.querySelector(".word-num");
    const tRect = textEl.getBoundingClientRect();
    const nRect = numEl ? numEl.getBoundingClientRect() : null;

    const cX = (tRect.left + tRect.right) / 2 - canvasRect.left;
    const cY = (tRect.top + tRect.bottom) / 2 - canvasRect.top;

    // Ensure circle clears the number prefix with safe padding
    const numRight = nRect ? (nRect.right - canvasRect.left) : 0;
    const minLeft = numRight > 0 ? numRight + 12 : 0;
    let cW = Math.max(tRect.width + 56, 150);
    if (cX - cW / 2 < minLeft) {
      cW = Math.max(tRect.width + 30, (cX - minLeft) * 2 - 4);
    }
    const cH = Math.max(tRect.height + 36, 80);

    const circleNode = rc.ellipse(cX, cY, cW, cH, {
      seed: 201 + idx * 13,
      stroke: '#2563eb',
      strokeWidth: 4.5,
      roughness: 1.25,
    });
    circleNode.id = `rough-circle-${idx+1}`;
    circleNode.classList.add("rough-card-circle");
    roughSvg.appendChild(circleNode);

    cardRects.push(card.getBoundingClientRect());
  });

  // 3. Hand-sketched larger, clearly visible arrows between list cards (fixed seeds: 301, 351)
  for (let i = 0; i < cardRects.length - 1; i++) {
    const r1 = cardRects[i];
    const r2 = cardRects[i + 1];
    const arrowX = (r1.left + r1.right) / 2 - canvasRect.left;
    const y1 = (r1.bottom - canvasRect.top) + 2;
    const y2 = (r2.top - canvasRect.top) - 2;
    if (y2 > y1) {
      const shaft = rc.line(arrowX, y1, arrowX, y2, {
        seed: 301 + i * 17,
        stroke: '#1e40af',
        strokeWidth: 6.0,
        roughness: 1.1
      });
      shaft.classList.add("arrow-shaft");

      const head = rc.linearPath([
        [arrowX - 22, y2 - 20],
        [arrowX, y2],
        [arrowX + 22, y2 - 20]
      ], {
        seed: 351 + i * 17,
        stroke: '#1e40af',
        strokeWidth: 6.0,
        roughness: 1.1
      });
      head.classList.add("arrow-head");

      const arrowGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
      arrowGroup.id = `rough-arrow-${i+1}`;
      arrowGroup.classList.add("rough-arrow");
      arrowGroup.appendChild(shaft);
      arrowGroup.appendChild(head);
      roughSvg.appendChild(arrowGroup);
    }
  }

  // Prepare progressive drawing stroke-dasharray & stroke-dashoffset for each annotation
  window.__annotations.forEach(ann => {
    const node = document.getElementById(ann.id);
    if (!node) return;
    const paths = node.querySelectorAll("path");
    const pathData = [];
    paths.forEach(p => {
      const len = p.getTotalLength();
      p.style.strokeDasharray = len;
      p.style.strokeDashoffset = len;
      pathData.push({ el: p, len: len });
    });
    node.style.opacity = "0";
    window.__annotationDrawers.push({
      id: ann.id,
      node: node,
      type: ann.type,
      start_ms: ann.start_ms,
      duration_ms: ann.duration_ms,
      paths: pathData,
    });
  });
}

// Call sketch initialization on page load
initRoughSketches();

window.seekAnimation = function(ms) {
  window.__timeline.seek(ms);

  // 1. Loudness-driven mouth sync for speaker
  const frameIdx = Math.floor((ms / 1000.0) * fps);
  const isOpen = (window.__mouthCues && window.__mouthCues[frameIdx]) || false;
  const speakerEl = document.getElementById(window.__speakerSlotId || "character-rig");
  if (speakerEl) {
    const mClosed = speakerEl.querySelector("#mouth-closed");
    const mOpen = speakerEl.querySelector("#mouth-wide_open") || speakerEl.querySelector("#mouth-open");
    if (mClosed && mOpen) {
      mClosed.style.display = isOpen ? "none" : "inline";
      mOpen.style.display = isOpen ? "inline" : "none";
    }
    // Speaker natural periodic blink
    const sBlink = (ms % 3800) < 140;
    const seBlink = speakerEl.querySelector("#eyes-blink");
    const seOpen = speakerEl.querySelector("#eyes-open");
    if (seBlink && seOpen) {
      seBlink.style.display = sBlink ? "inline" : "none";
      seOpen.style.display = sBlink ? "none" : "inline";
    }
  }

  // 2. Non-speaking listener character only blinks and glances, mouth stays closed
  if (window.__listenerSlotId) {
    const listenerEl = document.getElementById(window.__listenerSlotId);
    if (listenerEl) {
      const lmClosed = listenerEl.querySelector("#mouth-closed");
      if (lmClosed) lmClosed.style.display = "inline";
      const otherMouths = listenerEl.querySelectorAll(".mouth-state:not(#mouth-closed)");
      otherMouths.forEach(el => el.style.display = "none");

      const lBlink = ((ms + 1600) % 3200) < 140;
      const lGlance = ((ms + 800) % 4500) < 2200;
      const leBlink = listenerEl.querySelector("#eyes-blink");
      const leGlance = listenerEl.querySelector("#eyes-screen_left") || listenerEl.querySelector("#eyes-screen_right");
      const leOpen = listenerEl.querySelector("#eyes-open");

      if (leBlink && leOpen) {
        if (lBlink) {
          leBlink.style.display = "inline";
          leOpen.style.display = "none";
          if (leGlance) leGlance.style.display = "none";
        } else if (lGlance && leGlance) {
          leBlink.style.display = "none";
          leOpen.style.display = "none";
          leGlance.style.display = "inline";
        } else {
          leBlink.style.display = "none";
          leOpen.style.display = "inline";
          if (leGlance) leGlance.style.display = "none";
        }
      }
    }
  }

  // 3. Relaxed rest pose with gentle breathing sway only (NO constant bobbing)
  const charRig = document.getElementById("character-rig");
  if (charRig) {
    const breatheY = Math.sin(ms * 0.0015) * 1.5;
    charRig.style.transform = `translateY(${breatheY.toFixed(2)}px)`;
  }
  const charRigRight = document.getElementById("character-rig-right");
  if (charRigRight) {
    const breatheYRight = Math.sin((ms + 600) * 0.0015) * 1.5;
    charRigRight.style.transform = `scaleX(-1) translateY(${breatheYRight.toFixed(2)}px)`;
  }

  // 4. Purposeful gesture animation: raises at meaningful moment, holds, returns to rest with easing
  const gestType = window.__gestureType;
  const speakerElForGest = document.getElementById(window.__speakerSlotId || "character-rig");
  const gestArm = speakerElForGest ? speakerElForGest.querySelector(`#arm-gesture-${gestType}`) : document.getElementById(`arm-gesture-${gestType}`);
  const trigMs = window.__gestureTriggerMs;

  const restAngles = {
    wave: 132,
    point: 130,
    explain: 78,
    thumbs_up: 110,
    shrug: 45,
    idle: 0
  };
  const restDeg = restAngles[gestType] || 0;

  if (gestArm && gestType !== "idle") {
    const raiseDur = 350;
    const holdDur = 1100;
    const lowerDur = 400;
    const holdEnd = trigMs + raiseDur + holdDur;
    const animEnd = holdEnd + lowerDur;

    if (ms < trigMs) {
      gestArm.style.transform = `rotate(${restDeg}deg)`;
    } else if (ms < trigMs + raiseDur) {
      const t = (ms - trigMs) / raiseDur;
      // easeOutCubic
      const p = 1 - Math.pow(1 - t, 3);
      const curDeg = restDeg * (1 - p);
      gestArm.style.transform = `rotate(${curDeg.toFixed(2)}deg)`;
    } else if (ms < holdEnd) {
      if (gestType === "wave") {
        const waveSway = Math.sin((ms - trigMs - raiseDur) * 0.012) * 5;
        gestArm.style.transform = `rotate(${waveSway.toFixed(2)}deg)`;
      } else {
        gestArm.style.transform = "rotate(0deg)";
      }
    } else if (ms < animEnd) {
      const t = (ms - holdEnd) / lowerDur;
      // easeInOutQuad
      const p = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
      const curDeg = restDeg * p;
      gestArm.style.transform = `rotate(${curDeg.toFixed(2)}deg)`;
    } else {
      gestArm.style.transform = `rotate(${restDeg}deg)`;
    }
  } else if (gestArm) {
    gestArm.style.transform = "rotate(0deg)";
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
};
