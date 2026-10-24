import json
import math
from pathlib import Path
import pytest
from toonshorts.core import config

def smootherstep(t: float) -> float:
    c = max(0.0, min(1.0, t))
    return c * c * c * (c * (c * 6.0 - 15.0) + 10.0)

def compute_camera_state_py(ms: float, frame_idx: int, speaker_is_right: bool, stage_visuals: list, word_timings: list, tau_ms: float = 800.0):
    presets = {
        'wide': {'x': 0.0, 'y': 0.0, 'zoom': 1.0, 'focus': 'subject'},
        'boy_close': {'x': -130.0, 'y': -45.0, 'zoom': 1.18, 'focus': 'subject'},
        'girl_close': {'x': 130.0, 'y': -45.0, 'zoom': 1.18, 'focus': 'subject'},
        'board_close': {'x': 0.0, 'y': 90.0, 'zoom': 1.25, 'focus': 'board'},
    }
    speaker_preset_key = 'girl_close' if speaker_is_right else 'boy_close'
    speaker_preset = presets[speaker_preset_key]
    events = [{'t': 0, 'target': speaker_preset, 'focusVal': 0.0}]
    for vis in stage_visuals:
        trig = vis.get('start_ms', 0)
        dur = vis.get('duration_ms', 800)
        lead_start = max(0, trig - 400)
        events.append({'t': lead_start, 'target': presets['board_close'], 'focusVal': 1.0})
        return_start = trig + dur + 800
        events.append({'t': return_start, 'target': speaker_preset, 'focusVal': 0.0})
    events.sort(key=lambda x: x['t'])
    cur_x, cur_y, cur_zoom, cur_focus = presets['wide']['x'], presets['wide']['y'], presets['wide']['zoom'], 0.0
    prev_t = 0
    from_x, from_y, from_zoom, from_focus = cur_x, cur_y, cur_zoom, cur_focus
    to_x, to_y, to_zoom, to_focus = cur_x, cur_y, cur_zoom, cur_focus
    for ev in events:
        if ms < ev['t']:
            break
        elapsed_prev = ev['t'] - prev_t
        progress = min(1.0, elapsed_prev / tau_ms) if tau_ms > 0 else 1.0
        ease = smootherstep(progress)
        cur_x = from_x + ease * (to_x - from_x)
        cur_y = from_y + ease * (to_y - from_y)
        cur_zoom = from_zoom + ease * (to_zoom - from_zoom)
        cur_focus = from_focus + ease * (to_focus - from_focus)
        from_x, from_y, from_zoom, from_focus = cur_x, cur_y, cur_zoom, cur_focus
        to_x = ev['target']['x']
        to_y = ev['target']['y']
        to_zoom = ev['target']['zoom']
        to_focus = ev['focusVal']
        prev_t = ev['t']
    elapsed = ms - prev_t
    progress = min(1.0, elapsed / tau_ms) if tau_ms > 0 else 1.0
    ease = smootherstep(progress)
    base_cam_x = from_x + ease * (to_x - from_x)
    base_cam_y = from_y + ease * (to_y - from_y)
    base_cam_zoom = from_zoom + ease * (to_zoom - from_zoom)
    base_focus = from_focus + ease * (to_focus - from_focus)
    punch_zoom = 0.0
    punch_shake_x = 0.0
    punch_shake_y = 0.0
    if word_timings:
        rise_dur = 200
        decay_dur = 400
        total_dur = rise_dur + decay_dur
        max_punch = 0.050
        beats = []
        for wt in word_timings:
            w_clean = (wt.get('word') or '').lower()
            if any(k in w_clean for k in ('three', 'blue', 'blood', 'heart')):
                if not beats or wt.get('start_ms', 0) >= beats[-1] + total_dur:
                    beats.append(wt.get('start_ms', 0))
        for p_start in beats:
            if p_start <= ms < p_start + total_dur:
                delta_ms = ms - p_start
                if delta_ms < rise_dur:
                    zoom_boost = max_punch * math.sin((delta_ms / rise_dur) * (math.pi / 2.0))
                else:
                    decay_t = (delta_ms - rise_dur) / decay_dur
                    zoom_boost = max_punch * (1.0 - smootherstep(decay_t))
                punch_zoom = zoom_boost
                shake_decay = max(0.0, 1.0 - (delta_ms / (rise_dur + 100)))
                phase = frame_idx % 4
                punch_shake_x = (1.5 if phase == 1 else (-1.5 if phase == 3 else 0.0)) * shake_decay
                punch_shake_y = (1.2 if phase == 2 else (-1.2 if phase == 0 else 0.0)) * shake_decay
                break
    drift_x = 2.5 * math.sin(frame_idx * 0.035)
    drift_y = 1.8 * math.cos(frame_idx * 0.028)
    drift_rot = 0.35 * math.sin(frame_idx * 0.022)
    push_in_zoom = 1.0 + min(0.05, (ms / 6000.0) * 0.05)
    cam_x = base_cam_x + punch_shake_x
    cam_y = base_cam_y + punch_shake_y
    cam_zoom = (base_cam_zoom + punch_zoom) * push_in_zoom
    return {
        'camX': cam_x,
        'camY': cam_y,
        'camZoom': cam_zoom,
        'driftX': drift_x,
        'driftY': drift_y,
        'driftRot': drift_rot,
        'focus': base_focus,
    }

def test_camera_zoom_and_pan_frame_delta_limits():
    brief_path = Path('briefs/octopus_facts_v2_scene.json')
    assert brief_path.exists()
    scene_data = json.loads(brief_path.read_text(encoding='utf-8'))
    scenes = scene_data.get('scenes', [])[:4]
    fps = 30
    for s_idx, sc in enumerate(scenes):
        words = sc.get('word_timings', [])
        duration_sec = (words[-1]['end_time'] + 1.2) if words else 5.0
        total_frames = math.ceil(duration_sec * fps)
        word_timings_ms = [{'word': w['word'], 'start_ms': round(w['start_time'] * 1000), 'end_ms': round(w['end_time'] * 1000)} for w in words]
        stage_visuals = []
        for v in sc.get('visuals', []):
            start_ms = 1000
            for w in word_timings_ms:
                if (v.get('trigger_word') or '').lower() in w['word'].lower():
                    start_ms = w['start_ms']
                    break
            stage_visuals.append({'start_ms': start_ms, 'duration_ms': 1000})
        speaker_is_right = (sc.get('speaker') == 'girl_a')
        prev_state = compute_camera_state_py(0, 0, speaker_is_right, stage_visuals, word_timings_ms)
        max_d_zoom, max_d_x, max_d_y = 0.0, 0.0, 0.0
        for f in range(1, total_frames + 1):
            ms = f * (1000.0 / fps)
            cur_state = compute_camera_state_py(ms, f, speaker_is_right, stage_visuals, word_timings_ms)
            d_zoom = abs(cur_state['camZoom'] - prev_state['camZoom'])
            d_x = abs(cur_state['camX'] - prev_state['camX'])
            d_y = abs(cur_state['camY'] - prev_state['camY'])
            if d_zoom > max_d_zoom: max_d_zoom = d_zoom
            if d_x > max_d_x: max_d_x = d_x
            if d_y > max_d_y: max_d_y = d_y
            prev_state = cur_state
        assert max_d_zoom <= 0.02, f'Scene {s_idx + 1} max delta zoom {max_d_zoom} > 0.02'
        assert max_d_x <= 15.0, f'Scene {s_idx + 1} max delta panX {max_d_x} > 15.0 px'
        assert max_d_y <= 15.0, f'Scene {s_idx + 1} max delta panY {max_d_y} > 15.0 px'

def test_camera_zoom_monotonic_during_preset_transitions():
    brief_path = Path('briefs/octopus_facts_v2_scene.json')
    scene_data = json.loads(brief_path.read_text(encoding='utf-8'))
    scenes = scene_data.get('scenes', [])[:4]
    fps = 30
    for s_idx, sc in enumerate(scenes):
        speaker_is_right = (sc.get('speaker') == 'girl_a')
        for f in range(1, 24):
            prev_ms = (f - 1) * (1000.0 / fps)
            cur_ms = f * (1000.0 / fps)
            prev_state = compute_camera_state_py(prev_ms, f - 1, speaker_is_right, [], [])
            cur_state = compute_camera_state_py(cur_ms, f, speaker_is_right, [], [])
            assert cur_state['camZoom'] >= prev_state['camZoom'] - 1e-6, f'Scene {s_idx + 1} zoom reversed direction at frame {f}'
