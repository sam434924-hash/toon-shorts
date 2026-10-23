// Character Animation, Mouth Sync, Idle Life & Forward Kinematics (FK) Limb Math

// Computes snap rotation angle for right arm pointing toward active visual target
function computeArmSnapAngle(fkArmR, ms, trigMs, defaultAngle) {
  const defAng = (defaultAngle !== undefined) ? defaultAngle : -55.0;
  if (window.__enableArmSnap === false) return defAng;
  if (!fkArmR) return defAng;

  // 1. Locate active visual target from stage visuals or board cards
  let targetEl = null;
  const visuals = window.__stageVisuals || [];
  for (let i = 0; i < visuals.length; i++) {
    const v = visuals[i];
    const s = v.start_ms || 0;
    const d = v.duration_ms || 800;
    if (ms >= s && ms < s + d + 800) {
      targetEl = document.querySelector(v.target) || document.getElementById(v.dom_id);
      if (targetEl) break;
    }
  }

  // Fallback to board card if no stage visual is active
  if (!targetEl) {
    const cards = document.querySelectorAll('.card');
    if (cards && cards.length > 0) {
      targetEl = cards[0];
    }
  }

  // 2. Validate target existence, size, and on-stage boundaries
  if (!targetEl) return defAng;
  const r = targetEl.getBoundingClientRect();
  if (!r || r.width <= 0 || r.height <= 0) return defAng;

  const stageW = window.__stageWidth || 1080;
  const stageH = window.__stageHeight || 1920;
  if (r.right < 0 || r.bottom < 0 || r.left > stageW || r.top > stageH) {
    return defAng;
  }

  // 3. Resolve shoulder screen coordinates via SVG matrix transform
  const svgEl = fkArmR.ownerSVGElement;
  if (!svgEl || typeof svgEl.createSVGPoint !== 'function') return defAng;
  const pt = svgEl.createSVGPoint();
  pt.x = 585;
  pt.y = 525;
  const parentCtm = fkArmR.parentElement ? fkArmR.parentElement.getScreenCTM() : null;
  if (!parentCtm) return defAng;
  const screenSh = pt.matrixTransform(parentCtm);

  // 4. Compute elevation angle to target center and clamp to sane range [-75.0, -35.0]
  const tgtX = r.left + r.width / 2;
  const tgtY = r.top + r.height / 2;
  const dx = tgtX - screenSh.x;
  const dy = tgtY - screenSh.y;

  const thetaDeg = Math.atan2(dy, Math.abs(dx)) * (180 / Math.PI);
  return Math.max(-75.0, Math.min(-35.0, thetaDeg));
}

function seekLimbAnimation(ms, frameIdx) {
  const fps = window.__fps || 24;

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
        // Right arm raises upward pointing toward the active visual target
        const snapAngle = computeArmSnapAngle(fkArmR, ms, trigMs, -55.0);
        angShR = snapAngle * gPhase;
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
}

window.seekLimbAnimation = seekLimbAnimation;
window.computeArmSnapAngle = computeArmSnapAngle;
