# E-Signature Feature — Code Reference

**Project CP-004 · Klass Dignity Care Portal**
Feature 1: Electronic Signature & Intake Gateway

---

## Important: this feature has no backend code

The e-signature pipeline runs **entirely client-side in the browser**. `main.py` (the FastAPI
backend) contains **zero** signature-related code — verified by search.

The backend handles a *different* feature (the 24/7 chatbot, pricing engine, and lead capture
to `leads.json`). The signature never touches it — there is no API call, no upload, and no
server-side file write anywhere in this pipeline.

This is a genuine strength worth stating: the whole feature works with no server, no external
PDF library, and no paid e-signature service.

| Layer | File | Role |
|---|---|---|
| Structure | `index.html` | The canvas element and the signature slot inside the quote |
| Logic | `app.js` | Capture strokes, encode, embed, trigger print |
| Print layout | `style.css` | Strips the app UI so only the quote is printed |

---

## The pipeline

```
[User Drawing] -> [HTML5 Canvas] -> [Base64 Conversion]
      -> [syncPDFSignature()] -> [Browser Print Engine] -> [Final Executed Quote]
```

| # | Stage | What actually runs |
|---|---|---|
| 1 | User Drawing | `mousedown`/`mousemove` + `touchstart`/`touchmove` listeners |
| 2 | HTML5 Canvas | `ctx.lineTo()` then `ctx.stroke()` |
| 3 | Base64 Conversion | `canvas.toDataURL()` returns a Base64 PNG data URL |
| 4 | Embed | `syncPDFSignature()` sets the image and flips the status |
| 5 | Print Engine | `window.print()` + the `@media print` stylesheet |
| 6 | Output | One-page PDF with signature, signer, timestamp, totals |

---

## 1. HTML structure — `index.html`

The signature slot inside the quotation document:

```html
<span>Authorized Client E-Signature</span>
<span id="pdf-signature-status"
  class="text-[8px] font-semibold px-2 py-0.5 rounded bg-fillColor
         text-textMuted border border-borderLight">PENDING SIGNATURE</span>

<img id="pdf-signature-image" class="max-h-full max-w-full object-contain hidden"
     alt="Client Signature">
<span id="pdf-signature-placeholder"
  class="text-[10px] text-textMuted/60 italic">Awaiting signature below...</span>
```

The signature pad itself:

```html
<canvas id="signature-canvas" class="w-full h-full block"></canvas>
```

The export button:

```html
<button id="btn-print-quote">
  <span>Print / Export Quote as PDF</span>
</button>
```

**Note:** `#pdf-signature-image` starts with the `hidden` class and an empty `src`.
JavaScript fills it in and removes `hidden` once a signature exists.

---

## 2. Capturing the signature — `app.js`

`setupSignaturePad()` configures the drawing context and attaches both mouse and touch
listeners, so the same pad works on a laptop and on a touch device.

```javascript
function setupSignaturePad() {
  ctx = canvas.getContext('2d');
  ctx.strokeStyle = '#2D1A12';
  ctx.lineWidth = 2.5;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  canvas.addEventListener('mousedown', (e) => {
    drawing = true;
    canvasLabelHint.style.opacity = '0';
    ctx.beginPath();
    const rect = canvas.getBoundingClientRect();
    ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
  });

  canvas.addEventListener('mousemove', (e) => {
    if (!drawing) return;
    const rect = canvas.getBoundingClientRect();
    ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
    ctx.stroke();
    state.hasSignature = true;
    syncPDFSignature();
  });

  canvas.addEventListener('mouseup', () => {
    drawing = false;
    ctx.closePath();
    state.savedSignatureDataUrl = canvas.toDataURL();
    syncPDFSignature();
  });

  canvas.addEventListener('mouseleave', () => {
    if (drawing) {
      drawing = false;
      ctx.closePath();
      state.savedSignatureDataUrl = canvas.toDataURL();
      syncPDFSignature();
    }
  });

  canvas.addEventListener('touchstart', (e) => {
    const touch = e.touches[0];
    const rect = canvas.getBoundingClientRect();
    drawing = true;
    canvasLabelHint.style.opacity = '0';
    ctx.beginPath();
    ctx.moveTo(touch.clientX - rect.left, touch.clientY - rect.top);
    e.preventDefault();
  }, { passive: false });

  canvas.addEventListener('touchmove', (e) => {
    if (!drawing) return;
    const touch = e.touches[0];
    const rect = canvas.getBoundingClientRect();
    ctx.lineTo(touch.clientX - rect.left, touch.clientY - rect.top);
    ctx.stroke();
    state.hasSignature = true;
    syncPDFSignature();
    e.preventDefault();
  }, { passive: false });

  canvas.addEventListener('touchend', () => {
    drawing = false;
    ctx.closePath();
    state.savedSignatureDataUrl = canvas.toDataURL();
    syncPDFSignature();
  });
}
```

**Key points**

- `getContext('2d')` gives the 2D rendering context used for all drawing.
- Mouse and touch are handled **separately** (`mousedown`/`mousemove` and
  `touchstart`/`touchmove`) — this is not the Pointer Events API.
- `e.preventDefault()` on touch stops the page scrolling while signing.
- `getBoundingClientRect()` converts screen coordinates into canvas coordinates.
- `state.hasSignature` is the flag the rest of the app checks before allowing export.

---

## 3. Embedding into the quote — `app.js`

`syncPDFSignature()` is our own function (not an external API). It converts the canvas to
Base64, injects it into the quotation, and updates the document status.

```javascript
function syncPDFSignature() {
  const pdfSignatureImage = document.getElementById('pdf-signature-image');
  const pdfSignaturePlaceholder = document.getElementById('pdf-signature-placeholder');
  const pdfSignatureStatus = document.getElementById('pdf-signature-status');
  const pdfSignerName = document.getElementById('pdf-signer-name');
  const pdfSignerDate = document.getElementById('pdf-signer-date');
  const pdfSignerVerification = document.getElementById('pdf-signer-verification');

  if (state.hasSignature && canvas) {
    try {
      const dataUrl = canvas.toDataURL();
      state.savedSignatureDataUrl = dataUrl;
      if (state.quoteId) {
        const activeDraft = state.drafts.find(d => d.id === state.quoteId);
        if (activeDraft) activeDraft.signatureDataUrl = dataUrl;
      }
      if (pdfSignatureImage) {
        pdfSignatureImage.src = dataUrl;
        pdfSignatureImage.classList.remove('hidden');
      }
      if (pdfSignaturePlaceholder) pdfSignaturePlaceholder.classList.add('hidden');
      if (pdfSignatureStatus) {
        pdfSignatureStatus.textContent = 'EXECUTED & VERIFIED';
        pdfSignatureStatus.className = 'text-[8px] font-bold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/30';
      }
      if (pdfSignerName) pdfSignerName.textContent = state.user.name || "Guest Family";
      if (pdfSignerDate) pdfSignerDate.textContent = state.timestamp || new Date().toLocaleString();
      if (pdfSignerVerification) pdfSignerVerification.classList.remove('hidden');
    } catch (e) {
      console.warn('Signature sync error:', e);
    }
  } else if (state.savedSignatureDataUrl) {
    if (pdfSignatureImage) {
      pdfSignatureImage.src = state.savedSignatureDataUrl;
      pdfSignatureImage.classList.remove('hidden');
    }
    if (pdfSignaturePlaceholder) pdfSignaturePlaceholder.classList.add('hidden');
    if (pdfSignatureStatus) {
      pdfSignatureStatus.textContent = 'EXECUTED & VERIFIED';
      pdfSignatureStatus.className = 'text-[8px] font-bold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/30';
    }
    if (pdfSignerName) pdfSignerName.textContent = state.user.name || "Guest Family";
    if (pdfSignerDate) pdfSignerDate.textContent = state.timestamp || new Date().toLocaleString();
    if (pdfSignerVerification) pdfSignerVerification.classList.remove('hidden');
  } else {
    if (pdfSignatureImage) {
      pdfSignatureImage.src = '';
      pdfSignatureImage.classList.add('hidden');
    }
    if (pdfSignaturePlaceholder) pdfSignaturePlaceholder.classList.remove('hidden');
    if (pdfSignatureStatus) {
      pdfSignatureStatus.textContent = 'PENDING SIGNATURE';
      pdfSignatureStatus.className = 'text-[8px] font-semibold px-2 py-0.5 rounded bg-fillColor text-textMuted border border-borderLight';
    }
    if (pdfSignerName) pdfSignerName.textContent = state.user.name || "Guest Family";
    if (pdfSignerDate) pdfSignerDate.textContent = 'Pending';
    if (pdfSignerVerification) pdfSignerVerification.classList.add('hidden');
  }
}
```

**What Base64 does here**

`canvas.toDataURL()` returns a string like:

```
data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAoAAAACWCAYAAAC...
```

Because the image becomes plain **text**, it can be assigned directly to an `<img>` `src`.
Nothing is written to disk and nothing is uploaded — the signature travels inside the page
itself. That is precisely why this feature needs no backend.

---

## 4. Clearing the signature — `app.js`

```javascript
btnClearCanvas.addEventListener('click', () => {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  state.hasSignature = false;
  state.savedSignatureDataUrl = null;
  canvasLabelHint.style.opacity = '1';
  syncPDFSignature();
});
```

`clearRect()` wipes the canvas, the state flags reset, and `syncPDFSignature()` runs again —
which reverts the quote to "PENDING SIGNATURE".

---

## 5. Exporting to PDF — `app.js`

```javascript
// Print button handler
const btnPrintQuote = document.getElementById('btn-print-quote');
if (btnPrintQuote) {
  btnPrintQuote.addEventListener('click', () => {
    window.print();
  });
}
```

A single call. The browser's built-in print engine produces the PDF; no external library
such as jsPDF or ReportLab is used.

---

## 6. The print stylesheet — `style.css`

This is what turns a phone-shaped web app into a clean printable document.

```css
@media print {
  body {
    background: white !important;
    background-image: none !important;
    color: #2D1A12 !important;
    padding: 0 !important;
    margin: 0 !important;
  }

  body::before,
  body::after {
    display: none !important;
  }

  .device-container {
    width: 100% !important;
    height: auto !important;
    padding: 0 !important;
    margin: 0 !important;
    box-shadow: none !important;
    border: none !important;
    background: transparent !important;
    transform: none !important;
    border-radius: 0 !important;
    overflow: visible !important;
  }

  .device-container::after,
  .device-island,
  .home-indicator,
  .status-bar,
  #app-header,
  #app-nav {
    display: none !important;
  }

  .device-screen {
    border-radius: 0 !important;
    background: transparent !important;
    height: auto !important;
    width: 100% !important;
    overflow: visible !important;
  }

  /* Hide all other screens */
  #screen-1,
  #screen-2,
  #screen-3,
  #screen-4,
  #success-overlay {
    display: none !important;
  }

  #screen-5 {
    display: block !important;
    position: static !important;
    opacity: 1 !important;
    transform: none !important;
    width: 100% !important;
    max-width: 600px;
```

**What it does**

- Hides the device frame, status bar, header, and navigation.
- Hides every screen except `#screen-5` (the quotation).
- Hides the signature pad and buttons — the printed copy shows the *signed result*, not the
  input controls.
- Sets `page-break-inside: avoid` so the quote card is not split across pages.

---

## Testing status

| Platform | Input | Status |
|---|---|---|
| PC / Laptop | Mouse, trackpad | Tested and working |
| Tablet / Smartphone | Finger, stylus | Handlers written, not yet tested on a device |

---

## Scope (proof of concept)

- Signature capture and PDF embedding are fully functional.
- The `SHA256-SIGN` text shown on the quote is a **visual placeholder** marking where
  production cryptographic signing would be added. No hashing is performed.
- Signatures persist in browser memory and in the saved draft, not in a database.
