// Multiplane Parallax & Camera Presets Deterministic Engine
// Smootherstep Hermite interpolation: 6t^5 - 15t^4 + 10t^3
function smootherstep(t) {
  const c = Math.max(0, Math.min(1, t));
  return c * c * c * (c * (c * 6 - 15) + 10);
}

function computeCameraState(ms, frameIdx) {
  const pFactors = window.__cameraParallax || { foreground: 2.0, subject: 1.0, board: 0.5, deep_bg: 0.12 };
  const presets = window.__cameraPresets || {
    wide: { x: 0.0, y: 0.0, zoom: 1.0, focus: 'subject' },
    boy_close: { x: 130.0, y: -45.0, zoom: 1.18, focus: 'subject' },
    girl_close: { x: -130.0, y: -45.0, zoom: 1.18, focus: 'subject' },
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
        if (deltaMs < riseDur) {
          // Ease-out rise
          zoomBoost = maxPunch * Math.sin((deltaMs / riseDur) * (Math.PI / 2));
        } else {
          // Smootherstep decay
          const decayT = (deltaMs - riseDur) / decayDur;
          zoomBoost = maxPunch * (1.0 - smootherstep(decayT));
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
  const p = camState.pFactors;
  const layers = [
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

  // Rack Focus Blur Application with continuous ramp
  const f = typeof camState.focus === 'number' ? camState.focus : (camState.focus === 'board' ? 1.0 : 0.0);
  const rf = camState.cfg.rack_focus || { sharp: 0.0, near_defocus: 2.2, far_defocus: 3.8 };

  const fgEl = document.getElementById('layer-foreground');
  const subjEl = document.getElementById('layer-subject');
  const boardEl = document.getElementById('layer-board');
  const bgEl = document.getElementById('layer-deep-bg');

  const fgBlur = rf.near_defocus + f * (rf.far_defocus - rf.near_defocus);
  const subjBlur = rf.sharp + f * (rf.near_defocus - rf.sharp);
  const boardBlur = rf.near_defocus * (1.0 - f);
  const bgBlur = rf.far_defocus;

  if (fgEl) fgEl.style.filter = 'blur(' + fgBlur.toFixed(2) + 'px)';
  if (subjEl) subjEl.style.filter = 'blur(' + subjBlur.toFixed(2) + 'px)';
  if (boardEl) boardEl.style.filter = 'blur(' + boardBlur.toFixed(2) + 'px)';
  if (bgEl) bgEl.style.filter = 'blur(' + bgBlur.toFixed(2) + 'px)';
}

window.smootherstep = smootherstep;
window.computeCameraState = computeCameraState;
window.applyMultiplaneParallax = applyMultiplaneParallax;
