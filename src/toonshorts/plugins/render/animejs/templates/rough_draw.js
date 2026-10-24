// Store stroke drawing items for progressive animated line drawing
window.__annotationDrawers = [];

function wrapKeywordSpan(el, keyword) {
  if (!el || !keyword) return null;
  const cleanKw = keyword.toLowerCase().replace(/[^\w]/g, "");
  if (!cleanKw) return null;

  const fullText = el.textContent || "";
  const regex = new RegExp(`\\b${cleanKw}\\b`, "i");
  let match = fullText.match(regex);
  if (!match) {
    const subIdx = fullText.toLowerCase().indexOf(cleanKw);
    if (subIdx !== -1) {
      match = { index: subIdx, 0: fullText.substring(subIdx, subIdx + cleanKw.length) };
    }
  }
  if (!match || match.index === undefined) return null;

  const matchIdx = match.index;
  const matchLen = match[0].length;
  const beforeText = fullText.substring(0, matchIdx);
  const matchedText = fullText.substring(matchIdx, matchIdx + matchLen);
  const afterText = fullText.substring(matchIdx + matchLen);

  el.textContent = "";
  if (beforeText) el.appendChild(document.createTextNode(beforeText));
  const span = document.createElement("span");
  span.className = "wb-title-keyword";
  span.textContent = matchedText;
  el.appendChild(span);
  if (afterText) el.appendChild(document.createTextNode(afterText));

  return span;
}

// Initialize Rough.js Sketch Drawings with Fixed Deterministic Seeds
function initRoughSketches() {
  const roughSvg = document.getElementById("rough-canvas");
  const wbEl = document.querySelector(".whiteboard-outer");
  if (!roughSvg || !wbEl || typeof rough === "undefined") return;

  // 1. Idempotency: clear previous paths and reset drawers
  while (roughSvg.firstChild) {
    roughSvg.removeChild(roughSvg.firstChild);
  }
  window.__annotationDrawers = [];

  const rc = rough.svg(roughSvg);
  const canvasRect = roughSvg.getBoundingClientRect();
  const baseSeed = (typeof window.__roughSeed === "number") ? window.__roughSeed : 0;
  const isFast = !!window.__isFast;
  const roughnessMult = isFast ? 0.0 : 1.0;
  const bowingMult = isFast ? 0.0 : 1.0;

  // 2. Measure in resting position: temporarily reset animation transforms
  const titleEl = document.getElementById("wb-title");
  let prevTitleTransform = "";
  if (titleEl) {
    prevTitleTransform = titleEl.style.transform;
    titleEl.style.transform = "none";
  }

  const cards = document.querySelectorAll(".word-card");
  const prevCardTransforms = [];
  cards.forEach(card => {
    prevCardTransforms.push(card.style.transform);
    card.style.transform = "none";
  });

  // 1. Hand-sketched underline under the title keyword (or fallback full-width)
  if (titleEl) {
    const uAnn = (window.__annotations || []).find(a => a.type === "underline" || a.id === "rough-title-underline");
    const targetWord = uAnn ? uAnn.tied_word : null;
    let keywordSpan = null;
    if (targetWord) {
      keywordSpan = wrapKeywordSpan(titleEl, targetWord);
    }

    const rects = keywordSpan ? keywordSpan.getClientRects() : null;
    if (rects && rects.length > 0) {
      // Underline specific keyword (supports per-line underlines if wrapped across lines)
      const uGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
      uGroup.id = "rough-title-underline";
      Array.from(rects).forEach((r, rIdx) => {
        const leftX = (r.left - canvasRect.left) - 2;
        const rightX = (r.right - canvasRect.left) + 2;
        const underY = (r.bottom - canvasRect.top) + 4;
        const lineNode = rc.line(leftX, underY, rightX, underY, {
          seed: 101 + baseSeed + rIdx * 7,
          stroke: "#f59e0b",
          strokeWidth: 4.5,
          roughness: 1.3 * roughnessMult,
          bowing: 1.2 * bowingMult,
        });
        uGroup.appendChild(lineNode);
      });
      roughSvg.appendChild(uGroup);
    } else {
      // Fallback: full-width underline across the title badge container
      const tRect = titleEl.getBoundingClientRect();
      const leftX = (tRect.left - canvasRect.left) + 16;
      const rightX = (tRect.right - canvasRect.left) - 16;
      const underY = (tRect.bottom - canvasRect.top) + 8;
      const uLine = rc.line(leftX, underY, rightX, underY, {
        seed: 101 + baseSeed,
        stroke: "#f59e0b",
        strokeWidth: 5.5,
        roughness: 1.3 * roughnessMult,
        bowing: 1.2 * bowingMult,
      });
      uLine.id = "rough-title-underline";
      roughSvg.appendChild(uLine);
    }
  }

  // 2. Hand-sketched circles around keyword text (NOT list numbers)
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

    const cardAnn = (window.__annotations || []).find(a => a.card_index === idx || a.id === `rough-circle-${idx+1}` || a.id === `rough-box-${idx+1}`);
    const isBox = cardAnn && cardAnn.type === "box";

    let sketchNode;
    if (isBox) {
      sketchNode = rc.rectangle(cX - cW / 2, cY - cH / 2, cW, cH, {
        seed: 201 + baseSeed + idx * 13, stroke: '#2563eb', strokeWidth: 4.5, roughness: 1.25 * roughnessMult,
      });
      sketchNode.id = `rough-box-${idx+1}`;
      sketchNode.classList.add("rough-card-box");
    } else {
      sketchNode = rc.ellipse(cX, cY, cW, cH, {
        seed: 201 + baseSeed + idx * 13, stroke: '#2563eb', strokeWidth: 4.5, roughness: 1.25 * roughnessMult,
      });
      sketchNode.id = `rough-circle-${idx+1}`;
      sketchNode.classList.add("rough-card-circle");
    }
    roughSvg.appendChild(sketchNode);

    cardRects.push(card.getBoundingClientRect());
  });

  // 3. Hand-sketched larger, clearly visible arrows between list cards
  for (let i = 0; i < cardRects.length - 1; i++) {
    const r1 = cardRects[i];
    const r2 = cardRects[i + 1];
    const arrowX = (r1.left + r1.right) / 2 - canvasRect.left;
    const y1 = (r1.bottom - canvasRect.top) + 2;
    const y2 = (r2.top - canvasRect.top) - 2;
    if (y2 > y1) {
      const shaft = rc.line(arrowX, y1, arrowX, y2, {
        seed: 301 + baseSeed + i * 17,
        stroke: '#1e40af',
        strokeWidth: 6.0,
        roughness: 1.1 * roughnessMult,
        bowing: 1.0 * bowingMult
      });
      shaft.classList.add("arrow-shaft");

      const head = rc.linearPath([
        [arrowX - 22, y2 - 20],
        [arrowX, y2],
        [arrowX + 22, y2 - 20]
      ], {
        seed: 351 + baseSeed + i * 17,
        stroke: '#1e40af',
        strokeWidth: 6.0,
        roughness: 1.1 * roughnessMult,
        bowing: 1.0 * bowingMult
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

  // Restore transforms after resting-position measurements
  if (titleEl) {
    titleEl.style.transform = prevTitleTransform;
  }
  cards.forEach((card, idx) => {
    card.style.transform = prevCardTransforms[idx];
  });

  // Prepare progressive drawing stroke-dasharray & stroke-dashoffset for each annotation
  if (window.__annotations) {
    window.__annotations.forEach(ann => {
      const node = document.getElementById(ann.id);
      if (!node) return;
      const paths = node.querySelectorAll("path");
      const pathData = [];
      paths.forEach(p => {
        let len = 100;
        try {
          if (typeof p.getTotalLength === "function") len = p.getTotalLength() || 100;
        } catch (e) {}
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
    let len = 60;
    try {
      if (typeof p.getTotalLength === "function") len = p.getTotalLength() || 60;
    } catch (e) {}
    p.style.strokeDasharray = String(len);
    p.style.strokeDashoffset = String(len);
  });
}

// Export initialization function (invoked once on DOMContentLoaded / fonts ready)
window.initRoughSketches = initRoughSketches;
