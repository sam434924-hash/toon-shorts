// Multiplane Parallax & Camera Presets Deterministic Engine
// Smootherstep Hermite interpolation: 6t^5 - 15t^4 + 10t^3
function smootherstep(t) {
  const c = Math.max(0, Math.min(1, t));
  return c * c * c * (c * (c * 6 - 15) + 10);
}

// Ease-in-out cubic: monotonic Hermite curve without overshoot
function easeInOutCubic(t) {
  const c = Math.max(0, Math.min(1, t));
  return c < 0.5 ? 4 * c * c * c : 1 - Math.pow(-2 * c + 2, 3) / 2;
}

// Closed-form damped spring-mass solution (pure deterministic function of time)
function dampedSpring(t, omegaD, zeta) {
  if (t <= 0) return 0.0;
  if (t >= 1) return 1.0;
  const oD = (omegaD !== undefined) ? omegaD : (2 * Math.PI);
  const z = (zeta !== undefined) ? zeta : 0.65;
  const sZeta = Math.sqrt(1 - z * z);
  const omegaN = oD / sZeta;
  const decay = z * omegaN;
  const coeff = z / sZeta;
  const env = Math.exp(-decay * t) - t * Math.exp(-decay);
  const osc = Math.cos(oD * t) + coeff * Math.sin(oD * t);
  return 1.0 - env * osc;
}

function computeCameraState(ms, frameIdx) {
  const pFactors = window.__cameraParallax || { foreground: 2.0, subject: 1.0, board: 0.5, deep_bg: 0.12 };
  const presets = window.__cameraPresets || {
    wide: { x: 0.0, y: 0.0, zoom: 1.0, focus: 'subject' },
    boy_close: { x: -130.0, y: -45.0, zoom: 1.18, focus: 'subject' },
    girl_close: { x: 130.0, y: -45.0, zoom: 1.18, focus: 'subject' },
    board_close: { x: 0.0, y: 90.0, zoom: 1.25, focus: 'board' }
  };
  const cfg = window.__cameraConfig || {
    transition_sec: 0.80,
    drift_rot_max: 0.35,
    punch_in_zoom: 1.16,
    punch_in_shake: 1.5,
    rack_focus: { sharp: 0.0, near_defocus: 2.2, far_defocus: 3.8, transition_frames: 10 }
  };

  const isSpeakerRight = (window.__speakerSlotId || 'character-rig') === 'character-rig-right';
  const speakerPresetKey = isSpeakerRight ? 'girl_close' : 'boy_close';
  const speakerPreset = presets[speakerPresetKey] || presets.wide;
  const tau = ((cfg.transition_sec !== undefined) ? cfg.transition_sec : 0.80) * 1000.0;

  // Phase 4C: Two Independent Camera Zones Engine
  if (window.__enableSplitCameraZones === true) {
    const charFraming = window.__splitCameraFraming || {};
    const charShots = window.__splitCharShots || [];
    const boardShots = window.__splitBoardShots || [];

    function resolveCharCoords(targetName) {
      if (!targetName || targetName === 'wide') {
        return { x: 0.0, y: 0.0, zoom: 1.0 };
      }
      if (charFraming[targetName]) {
        return { x: charFraming[targetName].x, y: charFraming[targetName].y, zoom: charFraming[targetName].zoom };
      }
      const isRight = targetName.indexOf('right') !== -1 || targetName.indexOf('girl') !== -1 ||
        (isSpeakerRight && targetName.indexOf('left') === -1 && targetName.indexOf('boy') === -1);
      const fallbackKey = isRight ? 'speaker_right' : 'speaker_left';
      if (charFraming[fallbackKey]) {
        return { x: charFraming[fallbackKey].x, y: charFraming[fallbackKey].y, zoom: charFraming[fallbackKey].zoom };
      }
      return { x: 0.0, y: 0.0, zoom: 1.0 };
    }

    let charX = 0.0;
    let charY = 0.0;
    let charZoom = 1.0;

    if (charShots.length > 0) {
      if (ms < charShots[0].t_start) {
        const initC = resolveCharCoords(charShots[0].from_target);
        charX = initC.x;
        charY = initC.y;
        charZoom = initC.zoom;
      } else {
        let found = false;
        for (let i = 0; i < charShots.length; i++) {
          const s = charShots[i];
          if (ms >= s.t_start && ms <= s.t_end) {
            const p = (s.t_end > s.t_start) ? ((ms - s.t_start) / (s.t_end - s.t_start)) : 1.0;
            const ease = easeInOutCubic(p);
            const fromC = resolveCharCoords(s.from_target);
            const toC = resolveCharCoords(s.to_target);
            charX = fromC.x + ease * (toC.x - fromC.x);
            charY = fromC.y + ease * (toC.y - fromC.y);
            charZoom = fromC.zoom + ease * (toC.zoom - fromC.zoom);
            found = true;
            break;
          } else if (ms > s.t_end) {
            const nextShot = (i + 1 < charShots.length) ? charShots[i + 1] : null;
            if (!nextShot || ms < nextShot.t_start) {
              const toC = resolveCharCoords(s.to_target);
              charX = toC.x;
              charY = toC.y;
              charZoom = toC.zoom;
              found = true;
              break;
            }
          }
        }
        if (!found && charShots.length > 0) {
          const lastShot = charShots[charShots.length - 1];
          const toC = resolveCharCoords(lastShot.to_target);
          charX = toC.x;
          charY = toC.y;
          charZoom = toC.zoom;
        }
      }
    }

    const boardZoomPreset = window.__boardZoomTarget || 1.25;
    function resolveBoardCoords(targetName) {
      if (!targetName || targetName === 'wide') {
        return { x: 0.0, y: 0.0, zoom: 1.0 };
      }
      return { x: 0.0, y: 0.0, zoom: boardZoomPreset };
    }

    let boardX = 0.0;
    let boardY = 0.0;
    let boardZoom = 1.0;

    if (boardShots.length > 0) {
      if (ms < boardShots[0].t_start) {
        const initB = resolveBoardCoords(boardShots[0].from_target);
        boardX = initB.x;
        boardY = initB.y;
        boardZoom = initB.zoom;
      } else {
        let foundB = false;
        for (let i = 0; i < boardShots.length; i++) {
          const s = boardShots[i];
          if (ms >= s.t_start && ms <= s.t_end) {
            const p = (s.t_end > s.t_start) ? ((ms - s.t_start) / (s.t_end - s.t_start)) : 1.0;
            const ease = easeInOutCubic(p);
            const fromB = resolveBoardCoords(s.from_target);
            const toB = resolveBoardCoords(s.to_target);
            boardX = fromB.x + ease * (toB.x - fromB.x);
            boardY = fromB.y + ease * (toB.y - fromB.y);
            boardZoom = fromB.zoom + ease * (toB.zoom - fromB.zoom);
            foundB = true;
            break;
          } else if (ms > s.t_end) {
            const nextShot = (i + 1 < boardShots.length) ? boardShots[i + 1] : null;
            if (!nextShot || ms < nextShot.t_start) {
              const toB = resolveBoardCoords(s.to_target);
              boardX = toB.x;
              boardY = toB.y;
              boardZoom = toB.zoom;
              foundB = true;
              break;
            }
          }
        }
        if (!foundB && boardShots.length > 0) {
          const lastShot = boardShots[boardShots.length - 1];
          const toB = resolveBoardCoords(lastShot.to_target);
          boardX = toB.x;
          boardY = toB.y;
          boardZoom = toB.zoom;
        }
      }
    }

    const state = {
      board: {
        camX: boardX,
        camY: boardY,
        camZoom: boardZoom,
      },
      character: {
        camX: charX,
        camY: charY,
        camZoom: charZoom,
      },
      driftX: 0.0,
      driftY: 0.0,
      driftRot: 0.0,
      pFactors: {},
      cfg: cfg,
    };
    window.__lastCameraState = state;
    return state;
  }

  // Phase 4B: Purposeful Camera Shot Plan (deterministic pure function of time)
  if (window.__enablePurposefulCamera !== false && (cfg.mode === 'purposeful_only' || window.__cameraShotList !== undefined)) {
    const shotList = window.__cameraShotList || [];

    function resolveTargetCoords(targetName) {
      if (!targetName || targetName === 'wide') {
        return { x: presets.wide.x, y: presets.wide.y, zoom: presets.wide.zoom, focus: 0.0 };
      }
      if (presets[targetName]) {
        return { x: presets[targetName].x, y: presets[targetName].y, zoom: presets[targetName].zoom, focus: (presets[targetName].focus === 'board' ? 1.0 : 0.0) };
      }
      if (targetName === 'board_close' || targetName.indexOf('board_') === 0) {
        return { x: presets.board_close.x, y: presets.board_close.y, zoom: presets.board_close.zoom, focus: 1.0 };
      }
      if (targetName.indexOf('speaker_') === 0) {
        const isRight = targetName.indexOf('right') !== -1 || targetName.indexOf('girl') !== -1 ||
          (isSpeakerRight && targetName.indexOf('left') === -1 && targetName.indexOf('boy') === -1);
        const p = isRight ? presets.girl_close : presets.boy_close;
        return { x: p.x, y: p.y, zoom: p.zoom, focus: 0.0 };
      }
      return { x: presets.wide.x, y: presets.wide.y, zoom: presets.wide.zoom, focus: 0.0 };
    }

    let baseCamX = presets.wide.x;
    let baseCamY = presets.wide.y;
    let baseCamZoom = presets.wide.zoom;
    let baseFocus = 0.0;

    if (shotList.length > 0) {
      if (ms < shotList[0].t_start) {
        const initCoords = resolveTargetCoords(shotList[0].from_target);
        baseCamX = initCoords.x;
        baseCamY = initCoords.y;
        baseCamZoom = initCoords.zoom;
        baseFocus = initCoords.focus;
      } else {
        let found = false;
        for (let i = 0; i < shotList.length; i++) {
          const s = shotList[i];
          if (ms >= s.t_start && ms <= s.t_end) {
            const p = (s.t_end > s.t_start) ? ((ms - s.t_start) / (s.t_end - s.t_start)) : 1.0;
            const ease = easeInOutCubic(p);
            const fromC = resolveTargetCoords(s.from_target);
            const toC = resolveTargetCoords(s.to_target);
            baseCamX = fromC.x + ease * (toC.x - fromC.x);
            baseCamY = fromC.y + ease * (toC.y - fromC.y);
            baseCamZoom = fromC.zoom + ease * (toC.zoom - fromC.zoom);
            baseFocus = fromC.focus + ease * (toC.focus - fromC.focus);
            found = true;
            break;
          } else if (ms > s.t_end) {
            const nextShot = (i + 1 < shotList.length) ? shotList[i + 1] : null;
            if (!nextShot || ms < nextShot.t_start) {
              const toC = resolveTargetCoords(s.to_target);
              baseCamX = toC.x;
              baseCamY = toC.y;
              baseCamZoom = toC.zoom;
              baseFocus = toC.focus;
              found = true;
              break;
            }
          }
        }
        if (!found) {
          const lastShot = shotList[shotList.length - 1];
          const toC = resolveTargetCoords(lastShot.to_target);
          baseCamX = toC.x;
          baseCamY = toC.y;
          baseCamZoom = toC.zoom;
          baseFocus = toC.focus;
        }
      }
    }

    // Zero continuous drift when continuous_drift is false
    const driftX = (cfg.continuous_drift === true) ? (2.5 * Math.sin(frameIdx * 0.035)) : 0.0;
    const driftY = (cfg.continuous_drift === true) ? (1.8 * Math.cos(frameIdx * 0.028)) : 0.0;
    const driftRot = (cfg.continuous_drift === true) ? ((cfg.drift_rot_max || 0.35) * Math.sin(frameIdx * 0.022)) : 0.0;

    // Preserve Phase 4 closed-form damped spring punch-in on surprise words
    let punchZoom = 0.0;
    let punchShakeX = 0.0;
    let punchShakeY = 0.0;
    if (window.__wordTimings && window.__wordTimings.length > 0) {
      const riseDur = 200;
      const decayDur = 400;
      const totalDur = riseDur + decayDur;
      const maxPunch = 0.050;

      const beats = [];
      for (let i = 0; i < window.__wordTimings.length; i++) {
        const wt = window.__wordTimings[i];
        const wClean = (wt.word || '').toLowerCase();
        if (wClean.includes('three') || wClean.includes('blue') || wClean.includes('blood') || wClean.includes('heart')) {
          if (beats.length === 0 || (wt.start_ms >= beats[beats.length - 1] + totalDur)) {
            beats.push(wt.start_ms);
          }
        }
      }

      for (let i = 0; i < beats.length; i++) {
        const pStart = beats[i];
        if (ms >= pStart && ms < pStart + totalDur) {
          const deltaMs = ms - pStart;
          let zoomBoost = 0.0;
          if (window.__enableSpringCamera !== false) {
            if (deltaMs < riseDur) {
              zoomBoost = maxPunch * dampedSpring(deltaMs / riseDur);
            } else {
              const decayT = (deltaMs - riseDur) / decayDur;
              zoomBoost = maxPunch * (1.0 - dampedSpring(decayT));
            }
          } else {
            if (deltaMs < riseDur) {
              zoomBoost = maxPunch * Math.sin((deltaMs / riseDur) * (Math.PI / 2));
            } else {
              const decayT = (deltaMs - riseDur) / decayDur;
              zoomBoost = maxPunch * (1.0 - smootherstep(decayT));
            }
          }
          punchZoom = zoomBoost;

          const shakeDecay = Math.max(0, 1.0 - (deltaMs / (riseDur + 100)));
          const shakePhase = (frameIdx % 4);
          punchShakeX = (shakePhase === 1 ? 1.5 : (shakePhase === 3 ? -1.5 : 0)) * shakeDecay;
          punchShakeY = (shakePhase === 2 ? 1.2 : (shakePhase === 0 ? -1.2 : 0)) * shakeDecay;
          break;
        }
      }
    }

    const camX = baseCamX + punchShakeX;
    const camY = baseCamY + punchShakeY;
    const camZoom = baseCamZoom + punchZoom;

    return {
      camX: camX,
      camY: camY,
      camZoom: camZoom,
      driftX: driftX,
      driftY: driftY,
      driftRot: driftRot,
      focus: baseFocus,
      pFactors: pFactors,
      cfg: cfg
    };
  }

  // Build sequential timeline events to compute interpolated base camera values
  // 1. Initial move from wide -> speaker starts at t=0
  const events = [];
  events.push({ t: 0, target: speakerPreset, focusVal: 0.0 });

  // 2. Board visuals: lead by 400ms before visual lands
  if (window.__stageVisuals && window.__stageVisuals.length > 0) {
    for (let i = 0; i < window.__stageVisuals.length; i++) {
      const vis = window.__stageVisuals[i];
      const trig = vis.start_ms || 0;
      const dur = vis.duration_ms || 800;
      const leadStart = Math.max(0, trig - 400);
      events.push({ t: leadStart, target: presets.board_close, focusVal: 1.0 });
      const returnStart = trig + dur + 800;
      events.push({ t: returnStart, target: speakerPreset, focusVal: 0.0 });
    }
  }

  // Sort events chronologically
  events.sort((a, b) => a.t - b.t);

  let curX = presets.wide.x;
  let curY = presets.wide.y;
  let curZoom = presets.wide.zoom;
  let curFocus = 0.0; // 0.0 = subject, 1.0 = board

  let prevT = 0;
  let fromX = curX;
  let fromY = curY;
  let fromZoom = curZoom;
  let fromFocus = curFocus;
  let toX = curX;
  let toY = curY;
  let toZoom = curZoom;
  let toFocus = curFocus;

  for (let i = 0; i < events.length; i++) {
    const ev = events[i];
    if (ms < ev.t) {
      break;
    }
    // Advance state to ev.t
    const elapsedSincePrev = ev.t - prevT;
    const progress = tau > 0 ? Math.min(1.0, elapsedSincePrev / tau) : 1.0;
    const ease = smootherstep(progress);

    curX = fromX + ease * (toX - fromX);
    curY = fromY + ease * (toY - fromY);
    curZoom = fromZoom + ease * (toZoom - fromZoom);
    curFocus = fromFocus + ease * (toFocus - fromFocus);

    fromX = curX;
    fromY = curY;
    fromZoom = curZoom;
    fromFocus = curFocus;
    toX = ev.target.x;
    toY = ev.target.y;
    toZoom = ev.target.zoom;
    toFocus = ev.focusVal;
    prevT = ev.t;
  }

  // Interpolate between prevT and ms towards (toX, toY, toZoom, toFocus)
  const elapsed = ms - prevT;
  const progress = tau > 0 ? Math.min(1.0, elapsed / tau) : 1.0;
  const ease = smootherstep(progress);

  const baseCamX = fromX + ease * (toX - fromX);
  const baseCamY = fromY + ease * (toY - fromY);
  const baseCamZoom = fromZoom + ease * (toZoom - fromZoom);
  const baseFocus = fromFocus + ease * (toFocus - fromFocus);

  // Check surprise beats for punch-in ('three', 'blue', 'blood', 'hearts')
  // Ease-out rise (200ms) and ease-in-out decay (400ms), peak +0.050 (stays well below +0.08)
  let punchZoom = 0.0;
  let punchShakeX = 0.0;
  let punchShakeY = 0.0;
  if (window.__wordTimings && window.__wordTimings.length > 0) {
    const riseDur = 200;
    const decayDur = 400;
    const totalDur = riseDur + decayDur;
    const maxPunch = 0.050;

    // Collect distinct surprise beat triggers separated by at least totalDur to prevent jumping
    const beats = [];
    for (let i = 0; i < window.__wordTimings.length; i++) {
      const wt = window.__wordTimings[i];
      const wClean = (wt.word || '').toLowerCase();
      if (wClean.includes('three') || wClean.includes('blue') || wClean.includes('blood') || wClean.includes('heart')) {
        if (beats.length === 0 || (wt.start_ms >= beats[beats.length - 1] + totalDur)) {
          beats.push(wt.start_ms);
        }
      }
    }

    for (let i = 0; i < beats.length; i++) {
      const pStart = beats[i];
      if (ms >= pStart && ms < pStart + totalDur) {
        const deltaMs = ms - pStart;
        let zoomBoost = 0.0;
        if (window.__enableSpringCamera !== false) {
          // Closed-form damped spring-mass response for punch-in zoom
          if (deltaMs < riseDur) {
            zoomBoost = maxPunch * dampedSpring(deltaMs / riseDur);
          } else {
            const decayT = (deltaMs - riseDur) / decayDur;
            zoomBoost = maxPunch * (1.0 - dampedSpring(decayT));
          }
        } else {
          // Fallback smootherstep easing
          if (deltaMs < riseDur) {
            zoomBoost = maxPunch * Math.sin((deltaMs / riseDur) * (Math.PI / 2));
          } else {
            const decayT = (deltaMs - riseDur) / decayDur;
            zoomBoost = maxPunch * (1.0 - smootherstep(decayT));
          }
        }
        punchZoom = zoomBoost;

        // 1 to 2px shake on landing (damped over rise phase)
        const shakeDecay = Math.max(0, 1.0 - (deltaMs / (riseDur + 100)));
        const shakePhase = (frameIdx % 4);
        punchShakeX = (shakePhase === 1 ? 1.5 : (shakePhase === 3 ? -1.5 : 0)) * shakeDecay;
        punchShakeY = (shakePhase === 2 ? 1.2 : (shakePhase === 0 ? -1.2 : 0)) * shakeDecay;
        break;
      }
    }
  }

  // Constant drift: tiny sine-wave in position and rotation < 0.4 deg
  const driftX = 2.5 * Math.sin(frameIdx * 0.035);
  const driftY = 1.8 * Math.cos(frameIdx * 0.028);
  const driftRot = (cfg.drift_rot_max || 0.35) * Math.sin(frameIdx * 0.022);

  // Slow push-in during long lines (up to 1.05)
  const pushInZoom = 1.0 + Math.min(0.05, (ms / 6000.0) * 0.05);

  const camX = baseCamX + punchShakeX;
  const camY = baseCamY + punchShakeY;
  const camZoom = (baseCamZoom + punchZoom) * pushInZoom;

  return {
    camX: camX,
    camY: camY,
    camZoom: camZoom,
    driftX: driftX,
    driftY: driftY,
    driftRot: driftRot,
    focus: baseFocus,
    pFactors: pFactors,
    cfg: cfg
  };
}

function applyMultiplaneParallax(camState) {
  if (window.__enableSplitCameraZones === true) {
    const boardEl = document.getElementById('board-camera-content');
    const charEl = document.getElementById('character-camera-content');
    if (boardEl && camState.board) {
      boardEl.style.transform = 'translate(' + camState.board.camX.toFixed(2) + 'px, ' + camState.board.camY.toFixed(2) + 'px) scale(' + camState.board.camZoom.toFixed(3) + ')';
    }
    if (charEl && camState.character) {
      charEl.style.transform = 'translate(' + camState.character.camX.toFixed(2) + 'px, ' + camState.character.camY.toFixed(2) + 'px) scale(' + camState.character.camZoom.toFixed(3) + ')';
    }
    return;
  }

  // Safety Clamp: Ensure character real bounds (including swinging gesture arms) stay inside [margin, 1080 - margin]
  const margin = 24.0;
  const viewW = 1080.0;
  const isSpeakerRight = (window.__speakerSlotId || 'character-rig') === 'character-rig-right';

  const probeSubjEl = document.getElementById('layer-subject');
  if (probeSubjEl) {
    const fSubj = 1.0;
    const testShiftX = (-camState.camX * fSubj) + (camState.driftX * fSubj);
    const testShiftY = (-camState.camY * fSubj) + (camState.driftY * fSubj);
    const testScale = 1.0 + (camState.camZoom - 1.0) * Math.min(1.2, fSubj);
    probeSubjEl.style.transform = 'translate(' + testShiftX.toFixed(2) + 'px, ' + testShiftY.toFixed(2) + 'px) scale(' + testScale.toFixed(3) + ') rotate(' + camState.driftRot.toFixed(3) + 'deg)';

    let adjustX = 0.0;
    if (!isSpeakerRight) {
      const boyRoot = document.querySelector('#character-rig #character_root') || document.getElementById('character-rig');
      const boyArmL = document.querySelector('#character-rig #fk_arm_l');
      let boyMinLeft = Infinity;
      if (boyRoot) {
        const r = boyRoot.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) boyMinLeft = Math.min(boyMinLeft, r.left);
      }
      if (boyArmL) {
        const r = boyArmL.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) boyMinLeft = Math.min(boyMinLeft, r.left);
      }
      if (boyMinLeft < margin) {
        adjustX = -(margin - boyMinLeft + 1.0);
      }
    } else {
      const girlRoot = document.querySelector('#character-rig-right #character_root') || document.getElementById('character-rig-right');
      const girlArmR = document.querySelector('#character-rig-right #fk_arm_r');
      let girlMaxRight = -Infinity;
      if (girlRoot) {
        const r = girlRoot.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) girlMaxRight = Math.max(girlMaxRight, r.right);
      }
      if (girlArmR) {
        const r = girlArmR.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) girlMaxRight = Math.max(girlMaxRight, r.right);
      }
      if (girlMaxRight > viewW - margin) {
        adjustX = +(girlMaxRight - (viewW - margin) + 1.0);
      }
    }
    if (typeof adjustX === 'number' && !isNaN(adjustX) && adjustX !== 0.0) {
      camState.camX = Number(camState.camX) + adjustX;
    }
  }

  window.__lastCameraState = camState;

  const p = camState.pFactors;
  const layers = [
    { id: 'bg-layer-far', factor: p.bg_far || 0.08 },
    { id: 'bg-layer-mid', factor: p.bg_mid || 0.18 },
    { id: 'bg-layer-near', factor: p.bg_near || 0.32 },
    { id: 'layer-foreground', factor: p.foreground || 2.0 },
    { id: 'layer-subject', factor: p.subject || 1.0 },
    { id: 'layer-board', factor: p.board || 0.5 },
    { id: 'layer-deep-bg', factor: p.deep_bg || 0.12 }
  ];

  layers.forEach(item => {
    const el = document.getElementById(item.id);
    if (!el) return;
    const f = item.factor;
    const shiftX = (-camState.camX * f) + (camState.driftX * f);
    const shiftY = (-camState.camY * f) + (camState.driftY * f);
    const scale = 1.0 + (camState.camZoom - 1.0) * Math.min(1.2, f);
    el.style.transform = 'translate(' + shiftX.toFixed(2) + 'px, ' + shiftY.toFixed(2) + 'px) scale(' + scale.toFixed(3) + ') rotate(' + camState.driftRot.toFixed(3) + 'deg)';
  });

  const fgEl = document.getElementById('layer-foreground');
  const subjEl = document.getElementById('layer-subject');
  const boardEl = document.getElementById('layer-board');
  const bgEl = document.getElementById('layer-deep-bg');
  const bgFarEl = document.getElementById('bg-layer-far');
  const bgMidEl = document.getElementById('bg-layer-mid');
  const bgNearEl = document.getElementById('bg-layer-near');

  if (window.__isFast) {
    if (fgEl) fgEl.style.filter = 'none';
    if (subjEl) subjEl.style.filter = 'none';
    if (boardEl) boardEl.style.filter = 'none';
    if (bgEl) bgEl.style.filter = 'none';
    if (bgFarEl) bgFarEl.style.filter = 'none';
    if (bgMidEl) bgMidEl.style.filter = 'none';
    if (bgNearEl) bgNearEl.style.filter = 'none';
    return;
  }

  // Rack Focus Blur Application with continuous ramp
  const f = typeof camState.focus === 'number' ? camState.focus : (camState.focus === 'board' ? 1.0 : 0.0);
  const rf = camState.cfg.rack_focus || { sharp: 0.0, near_defocus: 2.2, far_defocus: 3.8 };

  const fgBlur = rf.near_defocus + f * (rf.far_defocus - rf.near_defocus);
  const subjBlur = rf.sharp + f * (rf.near_defocus - rf.sharp);
  const boardBlur = rf.near_defocus * (1.0 - f);
  const bgBlur = rf.far_defocus;

  function setFilterIfChanged(el, filterStr) {
    if (!el) return;
    if (el.__lastFilter !== filterStr) {
      el.style.filter = filterStr;
      el.__lastFilter = filterStr;
    }
  }

  setFilterIfChanged(fgEl, 'blur(' + fgBlur.toFixed(2) + 'px)');
  setFilterIfChanged(subjEl, 'blur(' + subjBlur.toFixed(2) + 'px)');
  setFilterIfChanged(boardEl, 'blur(' + boardBlur.toFixed(2) + 'px)');
  setFilterIfChanged(bgEl, 'blur(' + bgBlur.toFixed(2) + 'px)');
  setFilterIfChanged(bgFarEl, 'blur(' + (bgBlur * 1.2).toFixed(2) + 'px)');
  setFilterIfChanged(bgMidEl, 'blur(' + (bgBlur * 0.9).toFixed(2) + 'px)');
  setFilterIfChanged(bgNearEl, 'blur(' + (rf.near_defocus).toFixed(2) + 'px)');
}

window.smootherstep = smootherstep;
window.easeInOutCubic = easeInOutCubic;
window.dampedSpring = dampedSpring;
window.computeCameraState = computeCameraState;
window.applyMultiplaneParallax = applyMultiplaneParallax;
