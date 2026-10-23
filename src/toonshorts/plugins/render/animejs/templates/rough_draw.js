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
window.initRoughSketches = initRoughSketches;
