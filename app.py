"""
app.py  –  Image Stack Import Template Builder
Pattern Macro Hub theme. HTML inlined — no templates folder needed.
"""

import json
import os
import queue
import threading
import uuid
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file, stream_with_context
from processor import process_workbook

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

jobs: dict = {}
job_queues: dict = {}

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Image Stack Builder · Pattern</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0B1120;--bg2:#0F172A;--bg3:#111D33;
  --card:#131F38;--border:#1E2D4A;--border2:#243356;
  --blue:#3B82F6;--blue-bright:#60A5FA;
  --blue-dim:rgba(59,130,246,0.12);--blue-border:rgba(96,165,250,0.3);
  --teal:#2DD4BF;--teal-dim:rgba(45,212,191,0.1);--teal-border:rgba(45,212,191,0.3);
  --amber:#F59E0B;--amber-dim:rgba(245,158,11,0.08);--amber-border:rgba(245,158,11,0.35);
  --white:#F1F5F9;--muted:#64748B;--muted2:#94A3B8;
  --danger:#EF4444;--danger-dim:rgba(239,68,68,0.1);--danger-border:rgba(239,68,68,0.25);
  --success:#10B981;--success-dim:rgba(16,185,129,0.1);--success-border:rgba(16,185,129,0.25);
  --radius:10px;--radius-lg:14px;
}
html,body{min-height:100%;background:var(--bg);color:var(--white);font-family:'Sora',sans-serif;font-size:14px;line-height:1.6;-webkit-font-smoothing:antialiased}

/* ── Warning banner ── */
.warn-banner{background:var(--amber-dim);border-bottom:1px solid var(--amber-border);padding:11px 28px;display:flex;gap:10px;align-items:flex-start}
.warn-icon{color:var(--amber);font-size:15px;margin-top:2px;flex-shrink:0}
.warn-text{font-family:'IBM Plex Mono',monospace;font-size:11.5px;color:#CBD5E1;line-height:1.7}
.warn-text strong{color:var(--amber);font-weight:600}

/* ── Nav ── */
.topnav{background:var(--bg2);border-bottom:1px solid var(--border);padding:0 28px;height:52px;display:flex;align-items:center;justify-content:space-between}
.nav-left{display:flex;align-items:center;gap:10px}
.nav-logo{width:26px;height:26px;background:var(--blue);border-radius:6px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.nav-logo svg{width:14px;height:14px;fill:white}
.nav-title{font-size:13px;font-weight:700;color:var(--white);letter-spacing:-0.2px}
.nav-title span{color:var(--muted);font-weight:400;margin-left:4px;font-size:12px}

/* ── Page ── */
.page{max-width:780px;margin:0 auto;padding:32px 20px 100px}

/* ── Tool card ── */
.tool-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius-lg);overflow:hidden}

/* ── Card top ── */
.card-top{padding:22px 24px 18px}
.card-meta{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.card-icon{width:40px;height:40px;background:var(--blue-dim);border:1px solid var(--blue-border);border-radius:9px;display:flex;align-items:center;justify-content:center}
.card-icon svg{width:18px;height:18px;stroke:var(--blue-bright);stroke-width:1.8;fill:none;stroke-linecap:round;stroke-linejoin:round}
.badge-active{background:var(--teal-dim);border:1px solid var(--teal-border);color:var(--teal);font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;padding:3px 9px;border-radius:100px}
.card-title{font-size:17px;font-weight:700;color:var(--white);margin-bottom:7px;letter-spacing:-0.3px}
.card-desc{font-size:13px;color:var(--muted2);line-height:1.65;margin-bottom:14px}
.card-tags{display:flex;align-items:center;gap:6px}
.tag-folder{width:13px;height:13px;stroke:var(--amber);stroke-width:1.8;fill:none;flex-shrink:0}
.tag-text{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--amber)}
.tag-sep{color:var(--border2);margin:0 1px}

/* ── Card actions (template btn only) ── */
.card-actions{border-top:1px solid var(--border);padding:14px 24px;display:flex;gap:10px;align-items:center}
.btn-template{flex:0 0 auto;padding:9px 18px;background:transparent;border:1px solid var(--border2);color:var(--muted2);font-family:'Sora',sans-serif;font-size:13px;font-weight:600;border-radius:var(--radius);cursor:pointer;text-decoration:none;transition:all 0.15s;display:inline-flex;align-items:center;gap:7px}
.btn-template:hover{border-color:var(--blue-border);color:var(--white)}
.btn-template svg{width:13px;height:13px;stroke:currentColor;stroke-width:2.2;fill:none;stroke-linecap:round;stroke-linejoin:round}
.card-actions-hint{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted);margin-left:4px}

/* ── Upload panel (always visible) ── */
.upload-panel{border-top:1px solid var(--border);padding:20px 24px 24px}
.panel-inner{background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:18px}

/* Drop zone */
.upload-label{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.12em;color:var(--muted);margin-bottom:10px;display:block}
.drop-zone{border:1.5px dashed var(--border2);border-radius:var(--radius);padding:26px 20px;text-align:center;cursor:pointer;transition:all 0.2s;position:relative;background:var(--bg2)}
.drop-zone:hover,.drop-zone.dragging{border-color:var(--blue-bright);background:var(--blue-dim)}
.drop-zone input[type="file"]{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%}
.dz-icon{width:34px;height:34px;background:var(--bg3);border:1px solid var(--border);border-radius:8px;margin:0 auto 10px;display:flex;align-items:center;justify-content:center}
.dz-icon svg{width:15px;height:15px;stroke:var(--muted2);stroke-width:1.8;fill:none;stroke-linecap:round;stroke-linejoin:round}
.drop-zone h4{font-size:13px;font-weight:600;color:var(--white);margin-bottom:3px}
.drop-zone p{font-size:12px;color:var(--muted)}
.file-chip{display:none;margin-top:10px;align-items:center;gap:8px;background:var(--teal-dim);border:1px solid var(--teal-border);border-radius:7px;padding:8px 12px;font-size:12px;color:var(--teal);font-family:'IBM Plex Mono',monospace}
.file-chip.show{display:flex}
.file-chip svg{width:13px;height:13px;stroke:var(--teal);stroke-width:2;fill:none;flex-shrink:0}

/* Execute button */
.btn-execute{margin-top:14px;width:100%;padding:12px;background:var(--blue);color:white;font-family:'Sora',sans-serif;font-size:14px;font-weight:700;border:none;border-radius:var(--radius);cursor:pointer;transition:background 0.15s}
.btn-execute:hover:not(:disabled){background:var(--blue-bright)}
.btn-execute:disabled{opacity:0.35;cursor:not-allowed}

/* ── Progress ── */
.progress-wrap{margin-top:14px;display:none}
.progress-wrap.show{display:block}
.progress-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:7px}
.progress-lbl{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.12em;color:var(--muted)}
.progress-stat{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted2)}
.progress-track{background:var(--border);border-radius:100px;height:5px;overflow:hidden}
.progress-fill{height:100%;background:var(--blue);border-radius:100px;transition:width 0.3s ease;width:0%}
.progress-log{margin-top:7px;font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted);min-height:16px}

/* ── Result ── */
.result-wrap{margin-top:14px;display:none}
.result-wrap.show{display:block}
.result-box{border-radius:var(--radius);padding:13px 15px;display:flex;align-items:flex-start;gap:11px}
.result-box.success{background:var(--success-dim);border:1px solid var(--success-border)}
.result-box.error{background:var(--danger-dim);border:1px solid var(--danger-border)}
.r-icon{width:27px;height:27px;border-radius:7px;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px}
.result-box.success .r-icon{background:var(--success)}
.result-box.error .r-icon{background:var(--danger)}
.r-icon svg{width:13px;height:13px;stroke:white;stroke-width:2.5;fill:none;stroke-linecap:round;stroke-linejoin:round}
.r-text h5{font-size:13px;font-weight:700;color:var(--white);margin-bottom:2px}
.r-text p{font-size:12px;color:var(--muted2)}
.r-text p.err{color:#FCA5A5;font-family:'IBM Plex Mono',monospace;font-size:11px;word-break:break-all}
.result-actions{margin-top:12px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.btn-dl{display:inline-flex;align-items:center;gap:7px;padding:9px 18px;background:var(--blue);color:white;font-family:'Sora',sans-serif;font-size:13px;font-weight:700;border:none;border-radius:var(--radius);cursor:pointer;transition:background 0.15s}
.btn-dl:hover{background:var(--blue-bright)}
.btn-dl svg{width:13px;height:13px;stroke:white;stroke-width:2.5;fill:none;stroke-linecap:round;stroke-linejoin:round}
.btn-again{font-size:12px;color:var(--muted);background:none;border:none;cursor:pointer;text-decoration:underline;font-family:'Sora',sans-serif}
.btn-again:hover{color:var(--white)}

/* ── Skipped entries table ── */
.skipped-section{margin-top:16px;display:none}
.skipped-section.show{display:block}
.skipped-header{display:flex;align-items:center;gap:8px;margin-bottom:10px}
.skipped-badge{background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);color:#FCA5A5;font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;padding:3px 8px;border-radius:100px}
.skipped-title{font-size:12px;font-weight:600;color:var(--muted2)}
.skipped-note{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted);margin-bottom:10px;line-height:1.6}
.skipped-note span{color:#FCA5A5}
.skipped-table{width:100%;border-collapse:collapse;font-size:12px}
.skipped-table th{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted);padding:7px 10px;border-bottom:1px solid var(--border);text-align:left}
.skipped-table td{padding:8px 10px;border-bottom:1px solid rgba(30,45,74,0.6);vertical-align:top;color:var(--muted2);font-size:12px}
.skipped-table tr:last-child td{border-bottom:none}
.skipped-table td:first-child{font-family:'IBM Plex Mono',monospace;color:var(--white);font-weight:500}
.skipped-table td:nth-child(2){font-family:'IBM Plex Mono',monospace;color:var(--teal)}
.failed-url{display:block;font-family:'IBM Plex Mono',monospace;font-size:10px;color:#FCA5A5;word-break:break-all;margin-top:2px}
.failed-url::before{content:'↳ ';color:var(--danger)}

/* ── Footer ── */
.footer{background:var(--bg2);border-top:1px solid var(--border);padding:13px 28px;display:flex;justify-content:space-between;align-items:center;position:fixed;bottom:0;left:0;right:0}
.footer-left{display:flex;align-items:center;gap:9px}
.footer-logo{width:20px;height:20px;background:var(--blue);border-radius:4px;display:flex;align-items:center;justify-content:center}
.footer-logo svg{width:11px;height:11px;fill:white}
.footer-copy{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted)}
.footer-right{text-align:right}
.footer-credit{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted2)}
.footer-credit strong{color:var(--white);font-weight:600}
.footer-team{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--teal);margin-top:1px}
</style>
</head>
<body>

<div class="warn-banner">
  <span class="warn-icon">&#9888;</span>
  <div class="warn-text">
    <strong>Important notice:</strong> This tool operates based on specific data patterns. It may fail to deliver accurate results if the expected pattern is absent or has changed. <strong>Always verify the output data before use,</strong> especially when running the tool for the first time or after any source-format changes.
  </div>
</div>

<nav class="topnav">
  <div class="nav-left">
    <div class="nav-logo">
      <svg viewBox="0 0 14 14" xmlns="http://www.w3.org/2000/svg">
        <rect x="0" y="0" width="5.5" height="5.5" rx="1"/>
        <rect x="8.5" y="0" width="5.5" height="5.5" rx="1"/>
        <rect x="0" y="8.5" width="5.5" height="5.5" rx="1"/>
        <rect x="8.5" y="8.5" width="5.5" height="5.5" rx="1"/>
      </svg>
    </div>
    <span class="nav-title">Pattern Macro Hub <span>/ Image Stack Builder</span></span>
  </div>
</nav>

<div class="page">
  <div class="tool-card">

    <!-- Card header -->
    <div class="card-top">
      <div class="card-meta">
        <div class="card-icon">
          <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/></svg>
        </div>
        <span class="badge-active">Active</span>
      </div>
      <div class="card-title">Image Stack Import Builder</div>
      <div class="card-desc">Upload your filled Image Links workbook to resolve CDN filenames in parallel and generate a ready-to-import Image Stack Import Template sheet automatically.</div>
      <div class="card-tags">
        <svg class="tag-folder" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
        <span class="tag-text">Operations</span><span class="tag-sep">&middot;</span>
        <span class="tag-text">Media Stack</span><span class="tag-sep">&middot;</span>
        <span class="tag-text">PXM</span>
      </div>
    </div>

    <!-- Template download only -->
    <div class="card-actions">
      <a class="btn-template" href="https://drive.usercontent.google.com/u/0/uc?id=1qfhPnuQbFdkFv1tJZuSpxE-0I2brUxIp&export=download" target="_blank" rel="noopener">
        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        Download Template
      </a>
      <span class="card-actions-hint">Fill the template, then upload below to process.</span>
    </div>

    <!-- Upload panel — always visible -->
    <div class="upload-panel">
      <div class="panel-inner">
        <span class="upload-label">Upload workbook (.xlsx)</span>

        <div class="drop-zone" id="dropZone">
          <input type="file" id="fileInput" accept=".xlsx"/>
          <div class="dz-icon">
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          </div>
          <h4>Drop your file here</h4>
          <p>or click to browse</p>
        </div>

        <div class="file-chip" id="fileChip">
          <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span id="fileName"></span>
        </div>

        <button class="btn-execute" id="btnExecute" disabled>Build Import Template</button>

        <!-- Progress -->
        <div class="progress-wrap" id="progressWrap">
          <div class="progress-top">
            <span class="progress-lbl">Processing</span>
            <span class="progress-stat" id="progressStat">&mdash;</span>
          </div>
          <div class="progress-track"><div class="progress-fill" id="progressFill"></div></div>
          <div class="progress-log" id="progressLog">Scanning workbook&hellip;</div>
        </div>

        <!-- Result -->
        <div class="result-wrap" id="resultWrap"></div>

        <!-- Skipped entries -->
        <div class="skipped-section" id="skippedSection"></div>
      </div>
    </div>

  </div>
</div>

<footer class="footer">
  <div class="footer-left">
    <div class="footer-logo">
      <svg viewBox="0 0 14 14" xmlns="http://www.w3.org/2000/svg">
        <rect x="0" y="0" width="5.5" height="5.5" rx="1"/>
        <rect x="8.5" y="0" width="5.5" height="5.5" rx="1"/>
        <rect x="0" y="8.5" width="5.5" height="5.5" rx="1"/>
        <rect x="8.5" y="8.5" width="5.5" height="5.5" rx="1"/>
      </svg>
    </div>
    <span class="footer-copy">&copy; 2025 Pattern.</span>
  </div>
  <div class="footer-right">
    <div class="footer-credit">Designed by <strong>Akshay Kargutkar</strong></div>
    <div class="footer-team">Team Ops Avengers</div>
  </div>
</footer>

<script>
const dropZone     = document.getElementById('dropZone');
const fileInput    = document.getElementById('fileInput');
const fileChip     = document.getElementById('fileChip');
const fileNameEl   = document.getElementById('fileName');
const btnExecute   = document.getElementById('btnExecute');
const progressWrap = document.getElementById('progressWrap');
const progressFill = document.getElementById('progressFill');
const progressStat = document.getElementById('progressStat');
const progressLog  = document.getElementById('progressLog');
const resultWrap   = document.getElementById('resultWrap');
const skippedSection = document.getElementById('skippedSection');
let selectedFile = null;

fileInput.addEventListener('change', () => { const f = fileInput.files[0]; if (f) selectFile(f); });
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragging'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragging'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('dragging');
  const f = e.dataTransfer.files[0];
  if (f && f.name.endsWith('.xlsx')) selectFile(f);
});
function selectFile(f) {
  selectedFile = f; fileNameEl.textContent = f.name;
  fileChip.classList.add('show'); btnExecute.disabled = false;
}

btnExecute.addEventListener('click', async () => {
  if (!selectedFile) return;
  btnExecute.disabled = true;
  progressWrap.classList.add('show');
  resultWrap.classList.remove('show'); resultWrap.innerHTML = '';
  skippedSection.classList.remove('show'); skippedSection.innerHTML = '';
  progressFill.style.width = '0%';
  progressStat.textContent = '\u2014';
  progressLog.textContent = 'Uploading workbook\u2026';

  const fd = new FormData();
  fd.append('file', selectedFile);

  let jobId;
  try {
    const r = await fetch('/upload', { method: 'POST', body: fd });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || 'Upload failed');
    jobId = d.job_id;
  } catch(err) { showError(err.message); return; }

  progressLog.textContent = 'Fetching filenames from CDN\u2026';

  const es = new EventSource('/stream/' + jobId);
  es.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'progress') {
      const { done, total, pct, elapsed } = msg.data;
      progressFill.style.width = pct + '%';
      progressStat.textContent = done + ' / ' + total + ' \u00b7 ' + elapsed + 's';
      progressLog.textContent = 'Resolved ' + done + ' of ' + total + ' URLs\u2026';
    } else if (msg.type === 'done') {
      es.close();
      progressFill.style.width = '100%';
      progressStat.textContent = '100%';
      const d = msg.data;
      const skipped = d.failed_rows || [];
      progressLog.textContent = 'Complete \u2014 ' + d.written_rows + ' rows written' +
        (skipped.length ? ', ' + skipped.length + ' group(s) skipped.' : '.');
      showSuccess(jobId, d.written_rows, d.unique_urls, skipped);
    } else if (msg.type === 'error') {
      es.close(); showError(msg.data);
    }
  };
  es.onerror = () => { es.close(); showError('Connection lost. Please try again.'); };
});

function triggerDownload(jobId) {
  fetch('/download/' + jobId)
    .then(r => {
      if (!r.ok) return r.json().then(j => { throw new Error(j.error || 'Download failed'); });
      return r.blob();
    })
    .then(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'Image_Stack_Import_Template.xlsx';
      document.body.appendChild(a); a.click();
      setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1000);
    })
    .catch(err => showError(err.message));
}

function showSuccess(jobId, writtenRows, totalUrls, skippedRows) {
  const hasSkipped = skippedRows && skippedRows.length > 0;
  resultWrap.innerHTML =
    '<div class="result-box success">' +
    '<div class="r-icon"><svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><polyline points="20 6 9 17 4 12"/></svg></div>' +
    '<div class="r-text"><h5>Template ready</h5>' +
    '<p>' + writtenRows + ' rows written \u00b7 ' + totalUrls + ' URLs resolved' +
    (hasSkipped ? ' \u00b7 <span style="color:#FCA5A5">' + skippedRows.length + ' group(s) skipped</span>' : '') + '</p></div></div>' +
    '<div class="result-actions">' +
    '<button class="btn-dl" onclick="triggerDownload(\'' + jobId + '\')">' +
    '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' +
    'Download Template</button>' +
    '<button class="btn-again" onclick="resetUI()">Process another file</button>' +
    '</div>';
  resultWrap.classList.add('show');
  btnExecute.disabled = false;

  // Skipped entries table
  if (hasSkipped) {
    let rows = '';
    skippedRows.forEach(function(row) {
      const failedOnly = row.urls.filter(function(u) { return u.failed; });
      const urlLines = failedOnly.map(function(u) {
        return '<span class="failed-url">' + escHtml(u.url) + '</span>';
      }).join('');
      rows += '<tr>' +
        '<td>' + escHtml(row.master_id) + '</td>' +
        '<td>' + escHtml(row.stack_group) + '</td>' +
        '<td>' + urlLines + '</td>' +
        '</tr>';
    });
    skippedSection.innerHTML =
      '<div class="skipped-header">' +
      '<span class="skipped-badge">Skipped</span>' +
      '<span class="skipped-title">Entries excluded from output</span>' +
      '</div>' +
      '<div class="skipped-note">These groups were skipped because one or more image URLs could not be resolved. ' +
      'Fix the <span>highlighted cells</span> in the source workbook and re-run.</div>' +
      '<table class="skipped-table">' +
      '<thead><tr><th>Collection Folder</th><th>Stack Group</th><th>Failed URL(s)</th></tr></thead>' +
      '<tbody>' + rows + '</tbody>' +
      '</table>';
    skippedSection.classList.add('show');
  }
}

function showError(msg) {
  progressWrap.classList.remove('show');
  resultWrap.innerHTML =
    '<div class="result-box error">' +
    '<div class="r-icon"><svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></div>' +
    '<div class="r-text"><h5>Something went wrong</h5><p class="err">' + escHtml(msg) + '</p></div></div>' +
    '<div class="result-actions"><button class="btn-again" onclick="resetUI()">Try again</button></div>';
  resultWrap.classList.add('show');
  btnExecute.disabled = false;
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function resetUI() {
  selectedFile = null; fileInput.value = ''; fileNameEl.textContent = '';
  fileChip.classList.remove('show'); btnExecute.disabled = true;
  progressWrap.classList.remove('show');
  resultWrap.classList.remove('show'); resultWrap.innerHTML = '';
  skippedSection.classList.remove('show'); skippedSection.innerHTML = '';
  progressFill.style.width = '0%';
}
</script>
</body>
</html>"""


@app.route("/")
def index():
    return HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f or not f.filename.endswith(".xlsx"):
        return jsonify(error="Please upload a valid .xlsx file."), 400

    job_id   = str(uuid.uuid4())
    in_path  = UPLOAD_DIR / f"{job_id}_input.xlsx"
    out_path = OUTPUT_DIR / f"{job_id}_output.xlsx"
    f.save(in_path)

    q = queue.Queue()
    jobs[job_id] = {"status": "running", "progress": {}, "output": None, "error": None}
    job_queues[job_id] = q

    def run():
        try:
            def on_progress(done, total, elapsed):
                pct = round(done / total * 100)
                msg = {"done": done, "total": total, "pct": pct, "elapsed": round(elapsed, 1)}
                jobs[job_id]["progress"] = msg
                q.put(("progress", msg))

            result = process_workbook(
                file_path=in_path, output_path=out_path,
                progress_callback=on_progress,
            )
            # Strip non-serialisable objects before sending over SSE
            safe_result = {
                "rows":         result["rows"],
                "written_rows": result["written_rows"],
                "unique_urls":  result["unique_urls"],
                "output_sheet": result["output_sheet"],
                "failed_rows":  [
                    {
                        "master_id":   row["master_id"],
                        "stack_group": row["stack_group"],
                        "src_row":     row["src_row"],
                        "urls": [
                            {"url": u["url"], "failed": u["failed"], "filename": u["filename"],
                             "stack_order": u["stack_order"]}
                            for u in row["urls"]
                        ],
                    }
                    for row in result.get("failed_rows", [])
                ],
            }
            jobs[job_id]["status"] = "done"
            jobs[job_id]["output"] = str(out_path)
            q.put(("done", safe_result))
        except Exception as e:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"]  = str(e)
            q.put(("error", str(e)))
        finally:
            try:
                in_path.unlink()
            except Exception:
                pass

    threading.Thread(target=run, daemon=True).start()
    return jsonify(job_id=job_id)


@app.route("/stream/<job_id>")
def stream(job_id):
    if job_id not in job_queues:
        return jsonify(error="Job not found"), 404
    q = job_queues[job_id]

    @stream_with_context
    def generate():
        while True:
            try:
                event_type, data = q.get(timeout=60)
            except queue.Empty:
                yield 'data: {"type":"heartbeat"}\n\n'
                continue
            payload = json.dumps({"type": event_type, "data": data})
            yield f"data: {payload}\n\n"
            if event_type in ("done", "error"):
                break

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/download/<job_id>")
def download(job_id):
    job = jobs.get(job_id)
    if not job or job["status"] != "done":
        return jsonify(error="Output not ready"), 404
    out_path = job["output"]
    if not out_path or not Path(out_path).exists():
        return jsonify(error="Output file missing — session may have expired. Please re-run."), 404
    return send_file(
        out_path, as_attachment=True,
        download_name="Image_Stack_Import_Template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify(error="Job not found"), 404
    return jsonify({"status": job["status"], "progress": job["progress"], "error": job["error"]})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
