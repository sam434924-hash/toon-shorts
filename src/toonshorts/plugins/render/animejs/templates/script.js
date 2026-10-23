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
      seed: 101, stroke: '#f59e0b', strokeWidth: 5.5, roughness: 1.3, bowing: 1.2
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
      seed: 201 + idx * 13, stroke: '#2563eb', strokeWidth: 4.5, roughness: 1.25,
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
  if (window.__annotations) {
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

  // Initialize stage visual SVG paths for progressive stroke reveal
  document.querySelectorAll(".flow-arrow-svg path, .rr-arrow-svg path, .cc-icon-svg path").forEach(p => {
    const len = p.getTotalLength() || 60;
    p.style.strokeDasharray = String(len);
    p.style.strokeDashoffset = String(len);
  });
}

// Call sketch initialization on page load
initRoughSketches();

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

// Multiplane Parallax & Camera Presets Deterministic Engine
function computeCameraState(ms, frameIdx) {
  const pFactors = window.__cameraParallax || { foreground: 2.0, subject: 1.0, board: 0.5, deep_bg: 0.12 };
  const presets = window.__cameraPresets || {
    wide: { x: 0.0, y: 0.0, zoom: 1.0, focus: "subject" },
    boy_close: { x: 130.0, y: -45.0, zoom: 1.18, focus: "subject" },
    girl_close: { x: -130.0, y: -45.0, zoom: 1.18, focus: "subject" },
    board_close: { x: 0.0, y: 90.0, zoom: 1.25, focus: "board" }
  };
  const cfg = window.__cameraConfig || {
    transition_sec: 0.40,
    drift_rot_max: 0.35,
    punch_in_zoom: 1.16,
    punch_in_shake: 1.5,
    rack_focus: { sharp: 0.0, near_defocus: 2.2, far_defocus: 3.8, transition_frames: 10 }
  };

  const isSpeakerRight = (window.__speakerSlotId || "character-rig") === "character-rig-right";
  const speakerPresetKey = isSpeakerRight ? "girl_close" : "boy_close";

  // Leading move: start camera move 4 frames (~133ms) before visual/gesture lands
  const leadMs = 133;
  let nearestVisual = null;
  if (window.__stageVisuals && window.__stageVisuals.length > 0) {
    for (let i = 0; i < window.__stageVisuals.length; i++) {
      const vis = window.__stageVisuals[i];
      const trig = vis.start_ms || 0;
      if (ms >= (trig - leadMs) && ms < (trig + (vis.duration_ms || 800) + 2600)) {
        nearestVisual = vis;
        break;
      }
    }
  }

  // Check surprise beats for punch-in ("three", "blue", "blood", "hearts")
  let punchZoom = 0.0;
  let punchShakeX = 0.0;
  let punchShakeY = 0.0;
  if (window.__wordTimings && window.__wordTimings.length > 0) {
    for (let i = 0; i < window.__wordTimings.length; i++) {
      const wt = window.__wordTimings[i];
      const wClean = (wt.word || "").toLowerCase();
      if (wClean.includes("three") || wClean.includes("blue") || wClean.includes("blood") || wClean.includes("heart")) {
        const pStart = wt.start_ms;
        const pDur = 400;
        if (ms >= pStart && ms < pStart + pDur) {
          const punchProg = (ms - pStart) / pDur;
          // Zoom punch over ~2 frames
          const zoomBoost = punchProg < 0.20 ? (punchProg / 0.20) * 0.16 : 0.16 * (1.0 - (punchProg - 0.20) / 0.80);
          punchZoom = zoomBoost;
          // 1 to 2px shake on landing
          const shakeDecay = Math.max(0, 1.0 - punchProg * 2.5);
          const shakePhase = (frameIdx % 4);
          punchShakeX = (shakePhase === 1 ? 1.5 : (shakePhase === 3 ? -1.5 : 0)) * shakeDecay;
          punchShakeY = (shakePhase === 2 ? 1.2 : (shakePhase === 0 ? -1.2 : 0)) * shakeDecay;
          break;
        }
      }
    }
  }

  // Preset Selection & Easing
  let targetPreset = presets.wide;
  let targetFocus = "subject";

  if (nearestVisual) {
    targetPreset = presets.board_close;
    targetFocus = "board";
  } else if (ms >= 150 && ms < (window.__mainTimeline ? window.__mainTimeline.duration - 300 : 999999)) {
    targetPreset = presets[speakerPresetKey] || presets.wide;
    targetFocus = "subject";
  }

  // Constant drift: tiny sine-wave in position and rotation < 0.4 deg
  const driftX = 2.5 * Math.sin(frameIdx * 0.035);
  const driftY = 1.8 * Math.cos(frameIdx * 0.028);
  const driftRot = (cfg.drift_rot_max || 0.35) * Math.sin(frameIdx * 0.022);

  // Slow push-in during long lines (up to 1.05)
  const pushInZoom = 1.0 + Math.min(0.05, (ms / 6000.0) * 0.05);

  const camX = targetPreset.x + punchShakeX;
  const camY = targetPreset.y + punchShakeY;
  const camZoom = (targetPreset.zoom + punchZoom) * pushInZoom;

  return {
    camX,
    camY,
    camZoom,
    driftX,
    driftY,
    driftRot,
    focus: targetFocus,
    pFactors,
    cfg
  };
}

function applyMultiplaneParallax(camState) {
  const p = camState.pFactors;
  const layers = [
    { id: "layer-foreground", factor: p.foreground || 2.0 },
    { id: "layer-subject", factor: p.subject || 1.0 },
    { id: "layer-board", factor: p.board || 0.5 },
    { id: "layer-deep-bg", factor: p.deep_bg || 0.12 }
  ];

  layers.forEach(item => {
    const el = document.getElementById(item.id);
    if (!el) return;
    const f = item.factor;
    const shiftX = (-camState.camX * f) + (camState.driftX * f);
    const shiftY = (-camState.camY * f) + (camState.driftY * f);
    const scale = 1.0 + (camState.camZoom - 1.0) * Math.min(1.2, f);
    el.style.transform = `translate(${shiftX.toFixed(2)}px, ${shiftY.toFixed(2)}px) scale(${scale.toFixed(3)}) rotate(${camState.driftRot.toFixed(3)}deg)`;
  });

  // Rack Focus Blur Application
  const isBoardFocus = (camState.focus === "board");
  const rf = camState.cfg.rack_focus || { sharp: 0.0, near_defocus: 2.2, far_defocus: 3.8 };

  const fgEl = document.getElementById("layer-foreground");
  const subjEl = document.getElementById("layer-subject");
  const boardEl = document.getElementById("layer-board");
  const bgEl = document.getElementById("layer-deep-bg");

  if (fgEl) fgEl.style.filter = `blur(${isBoardFocus ? rf.far_defocus : rf.near_defocus}px)`;
  if (subjEl) subjEl.style.filter = `blur(${isBoardFocus ? rf.near_defocus : rf.sharp}px)`;
  if (boardEl) boardEl.style.filter = `blur(${isBoardFocus ? rf.sharp : rf.near_defocus}px)`;
  if (bgEl) bgEl.style.filter = `blur(${rf.far_defocus}px)`;
}

window.seekAnimation = function(ms) {
  if (window.__timeline) {
    window.__timeline.seek(ms);
  }

  const frameIdx = Math.floor((ms / 1000.0) * fps);

  // 0. Compute deterministic multiplane camera state & parallax shifts
  const camState = computeCameraState(ms, frameIdx);
  applyMultiplaneParallax(camState);

  // 1. Loudness-driven mouth sync for speaker
  const isOpen = (window.__mouthCues && window.__mouthCues[frameIdx]) || false;
  const speakerEl = document.getElementById(window.__speakerSlotId || "character-rig");
  if (speakerEl) {
    const mClosed = speakerEl.querySelector("#mouth-closed");
    const mOpen = speakerEl.querySelector("#mouth-wide_open") || speakerEl.querySelector("#mouth-open");
    if (mClosed && mOpen) {
      mClosed.style.display = isOpen ? "none" : "inline";
      mOpen.style.display = isOpen ? "inline" : "none";
    }

    const sBlink = ((ms + 400) % 3600) < 140;
    const seBlink = speakerEl.querySelector("#eyes-blink");
    const seOpen = speakerEl.querySelector("#eyes-open");
    if (seBlink && seOpen) {
      seBlink.style.display = sBlink ? "inline" : "none";
      seOpen.style.display = sBlink ? "none" : "inline";
    }
  }

  // 2. Listener glance toward speaker & independent blinking
  const listenerEl = document.getElementById(window.__listenerSlotId);
  if (listenerEl) {
    const lmClosed = listenerEl.querySelector("#mouth-closed");
    if (lmClosed) lmClosed.style.display = "inline";
    const otherMouths = listenerEl.querySelectorAll(".mouth-state:not(#mouth-closed)");
    otherMouths.forEach(el => el.style.display = "none");

    const lBlink = ((ms + 1600) % 3200) < 140;
    const lGlance = ((ms + 800) % 4500) < 2200;

    const isListenerRight = window.__listenerSlotId === "character-rig-right" || listenerEl.classList.contains("char-slot-right");
    const isSpeakerRight = (window.__speakerSlotId || "character-rig") === "character-rig-right";
    const speakerOnRight = isSpeakerRight && !isListenerRight;
    const screenDir = speakerOnRight ? "right" : "left";
    const targetEye = isListenerRight
      ? (screenDir === "left" ? "eyes-screen_right" : "eyes-screen_left")
      : (screenDir === "right" ? "eyes-screen_right" : "eyes-screen_left");
    const fallbackEye = (targetEye === "eyes-screen_right") ? "eyes-screen_left" : "eyes-screen_right";

    const leGlance = listenerEl.querySelector(`#${targetEye}`) || listenerEl.querySelector(`#${fallbackEye}`);
    const leBlink = listenerEl.querySelector("#eyes-blink");
    const leOpen = listenerEl.querySelector("#eyes-open");
    const activeEye = (lBlink && leBlink) ? leBlink : ((lGlance && leGlance) ? leGlance : leOpen);

    if (activeEye) {
      listenerEl.querySelectorAll(".eye-state").forEach(el => {
        el.style.display = (el === activeEye) ? "inline" : "none";
      });
    }
  }

  // 3. Idle life: breathing bob (~1.5s), micro head tilt, and speech squash
  const breatheY = Math.sin((ms / 1500.0) * 2 * Math.PI) * 1.8;
  const headTilt = Math.sin((ms / 2800.0) * 2 * Math.PI) * 0.7;
  const isLeftSpeaker = (window.__speakerSlotId || "character-rig") === "character-rig";
  const isRightSpeaker = (window.__speakerSlotId || "character-rig") === "character-rig-right";
  const leftSquash = (isLeftSpeaker && isOpen) ? "scale(1.012, 0.988)" : "scale(1.0, 1.0)";
  const rightSquash = (isRightSpeaker && isOpen) ? "scale(1.012, 0.988)" : "scale(1.0, 1.0)";

  const charRig = document.getElementById("character-rig");
  if (charRig) {
    charRig.style.transform = `translateY(${breatheY.toFixed(2)}px) rotate(${headTilt.toFixed(2)}deg) ${leftSquash}`;
  }
  const charRigRight = document.getElementById("character-rig-right");
  if (charRigRight) {
    const breatheYRight = Math.sin(((ms + 600) / 1500.0) * 2 * Math.PI) * 1.8;
    charRigRight.style.transform = `scaleX(-1) translateY(${breatheYRight.toFixed(2)}px) rotate(${(-headTilt).toFixed(2)}deg) ${rightSquash}`;
  }

  // 4. Purposeful gesture & FK full-body rig animation
  const gestType = window.__gestureType;
  const speakerElForGest = document.getElementById(window.__speakerSlotId || "character-rig");
  const trigMs = window.__gestureTriggerMs;

  // 4a. Standalone arm element fallback (e.g. presenter pack)
  const gestArm = speakerElForGest ? speakerElForGest.querySelector(`#arm-gesture-${gestType}`) : document.getElementById(`arm-gesture-${gestType}`);
  const restAngles = {
    wave: 132,
    point: 130,
    point_board: 130,
    point_other: 110,
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
      const p = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
      const curDeg = restDeg * p;
      gestArm.style.transform = `rotate(${curDeg.toFixed(2)}deg)`;
    } else {
      gestArm.style.transform = `rotate(${restDeg}deg)`;
    }
  } else if (gestArm) {
    gestArm.style.transform = "rotate(0deg)";
  }

  // 4b. Full-Body FK Rig Animation (boy_b, girl_a, and gesture-ready packs)
  if (speakerElForGest) {
    const fkArmR = speakerElForGest.querySelector("#fk_arm_r");
    const fkArmLowerR = speakerElForGest.querySelector("#fk_arm_lower_r");
    const fkArmL = speakerElForGest.querySelector("#fk_arm_l");
    const fkArmLowerL = speakerElForGest.querySelector("#fk_arm_lower_l");
    const fkHead = speakerElForGest.querySelector("#fk_head_base");

    if (fkArmR && fkArmLowerR) {
      // Joint pivot points from SVG transform or defaults
      const pShR = [585, 525];
      const pElR = [610, 660];
      const pShL = [415, 525];
      const pElL = [390, 660];
      const pHead = [500, 500];

      // Gesture phase calculation: anticipation -> quick arc -> hold -> return
      let gPhase = 0.0;
      let inHold = false;
      const raiseDur = 350;
      const holdDur = 1200;
      const lowerDur = 450;
      const holdEnd = trigMs + raiseDur + holdDur;
      const animEnd = holdEnd + lowerDur;

      if (ms >= trigMs && ms < trigMs + raiseDur) {
        const t = (ms - trigMs) / raiseDur;
        // Anticipation dip then snap arc
        if (t < 0.20) {
          gPhase = -0.08 * (t / 0.20);
        } else {
          const tNorm = (t - 0.20) / 0.80;
          gPhase = 1.0 - Math.pow(1.0 - tNorm, 3);
        }
      } else if (ms >= trigMs + raiseDur && ms < holdEnd) {
        gPhase = 1.0;
        inHold = true;
      } else if (ms >= holdEnd && ms < animEnd) {
        const t = (ms - holdEnd) / lowerDur;
        // Smooth return with ease-in-out
        gPhase = 1.0 - (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
      } else {
        gPhase = 0.0;
      }

      let angShR = 0, angElR = 0, angShL = 0, angElL = 0, angHead = 0;

      if (gestType === "point" || gestType === "point_board") {
        // Right arm raises upward pointing toward the board
        angShR = -55 * gPhase;
        angElR = -25 * gPhase;
        if (inHold) {
          angShR += Math.sin((ms - trigMs) * 0.005) * 1.5;
        }
      } else if (gestType === "point_other") {
        // Arm points inward toward other character
        angShR = 25 * gPhase;
        angElR = -45 * gPhase;
      } else if (gestType === "explain") {
        // Two-handed explain / open gestures
        angShR = -38 * gPhase;
        angElR = -28 * gPhase;
        angShL = 35 * gPhase;
        angElL = 25 * gPhase;
        if (inHold) {
          const emp = Math.sin((ms - trigMs) * 0.008) * 3;
          angShR += emp;
          angShL -= emp;
        }
      } else if (gestType === "wave") {
        angShR = -85 * gPhase;
        angElR = -40 * gPhase;
        if (inHold) {
          angElR += Math.sin((ms - trigMs - raiseDur) * 0.015) * 12;
        }
      } else if (gestType === "thumbs_up") {
        angShR = -45 * gPhase;
        angElR = -55 * gPhase;
      } else if (gestType === "shrug") {
        angShR = -18 * gPhase;
        angElR = -35 * gPhase;
        angShL = 18 * gPhase;
        angElL = 35 * gPhase;
        angHead = 6 * gPhase;
      } else if (gestType === "nod") {
        angHead = Math.sin((ms - trigMs) * 0.014) * 8 * gPhase;
      } else if (gestType === "head_tilt") {
        angHead = 7 * gPhase;
      }

      fkArmR.setAttribute("transform", `rotate(${angShR.toFixed(2)}, ${pShR[0]}, ${pShR[1]})`);
      fkArmLowerR.setAttribute("transform", `rotate(${angElR.toFixed(2)}, ${pElR[0]}, ${pElR[1]})`);
      if (fkArmL) fkArmL.setAttribute("transform", `rotate(${angShL.toFixed(2)}, ${pShL[0]}, ${pShL[1]})`);
      if (fkArmLowerL) fkArmLowerL.setAttribute("transform", `rotate(${angElL.toFixed(2)}, ${pElL[0]}, ${pElL[1]})`);
      if (fkHead && angHead !== 0) fkHead.setAttribute("transform", `rotate(${angHead.toFixed(2)}, ${pHead[0]}, ${pHead[1]})`);
    }
  }

  // 4c. Listener reactive subtle pose (nod, head tilt, glance at board)
  const listenerElForGest = document.getElementById(window.__listenerSlotId);
  if (listenerElForGest) {
    const lFkHead = listenerElForGest.querySelector("#fk_head_base");
    if (lFkHead) {
      // Subtly nod or tilt head during speaker turns
      const lNod = Math.sin((ms + 400) * 0.0035) * 2.2;
      const lTilt = Math.sin((ms + 900) * 0.0022) * 2.5;
      lFkHead.setAttribute("transform", `rotate(${(lNod + lTilt).toFixed(2)}, 500, 500)`);
    }
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
  if (window.updateStageVisuals) {
    window.updateStageVisuals(ms);
  }

  // 8. Deterministic night studio background motion (LED pulse, glow particles, twinkling windows)
  if (window.updateNightStudioEffects) {
    window.updateNightStudioEffects(ms);
  }
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

window.seekTo = window.seekAnimation;
