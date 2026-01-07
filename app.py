# Whisper Japanese Transcription Web App – Enhanced Professional UI
# CPU-only, offline-friendly, multi-audio library
# Tech stack: FastAPI + Whisper + SQLite + HTML/CSS/JS (no frontend framework)

import uuid
import os
import sqlite3
import json
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import whisper

UPLOAD_DIR = "uploads"
DB_PATH = "app.db"
CONFIG_PATH = "config.json"

# ----------------------
# Load Configuration
# ----------------------
def load_config():
    """Load configuration from config.json or create default"""
    default_config = {
        "language": "ja",
        "model_size": "base",
        "device": "cpu"
    }
    
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                # Merge with defaults for missing keys
                return {**default_config, **config}
        except Exception as e:
            print(f"Error loading config: {e}")
            print("Using default configuration")
    else:
        # Create default config file
        with open(CONFIG_PATH, 'w') as f:
            json.dump(default_config, f, indent=2)
        print("Created default config.json")
    
    return default_config

config = load_config()
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ----------------------
# Database setup
# ----------------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS audio (
    id TEXT PRIMARY KEY,
    filename TEXT,
    original_name TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS segments (
    audio_id TEXT,
    start REAL,
    end REAL,
    text TEXT
)
""")
conn.commit()

# ----------------------
# App & Model
# ----------------------
app = FastAPI()

# Load model with configured device and size
print(f"Loading Whisper model '{config['model_size']}' on device '{config['device']}'...")
model = whisper.load_model(config['model_size'], device=config['device'])
print("Model loaded successfully!")

# ----------------------
# UI
# ----------------------
@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Japanese Transcription Library</title>
  <style>
    * {
      box-sizing: border-box;
    }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: #1f2937;
      overflow: hidden;
    }
    header {
      padding: 24px 32px;
      background: rgba(255, 255, 255, 0.98);
      color: #1f2937;
      font-size: 24px;
      font-weight: 700;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      display: flex;
      align-items: center;
      gap: 12px;
    }
    header::before {
      content: "🎧";
      font-size: 32px;
    }
    main {
      display: grid;
      grid-template-columns: 320px 1fr;
      height: calc(100vh - 80px);
      margin: 16px;
      gap: 16px;
    }
    aside {
      background: rgba(255, 255, 255, 0.98);
      border-radius: 16px;
      padding: 20px;
      overflow-y: auto;
      box-shadow: 0 8px 32px rgba(0,0,0,0.12);
    }
    aside h3 {
      margin: 0 0 16px 0;
      font-size: 14px;
      text-transform: uppercase;
      color: #6b7280;
      font-weight: 600;
      letter-spacing: 0.5px;
    }
    .upload-section {
      margin-bottom: 24px;
      padding: 16px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 12px;
      color: white;
    }
    .upload-controls {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .file-input-wrapper {
      position: relative;
      overflow: hidden;
      display: inline-block;
      width: 100%;
    }
    .file-input-wrapper input[type=file] {
      position: absolute;
      left: -9999px;
    }
    .file-input-label {
      display: block;
      padding: 10px 16px;
      background: rgba(255,255,255,0.2);
      border: 2px dashed rgba(255,255,255,0.5);
      border-radius: 8px;
      cursor: pointer;
      text-align: center;
      transition: all 0.3s;
      font-size: 14px;
    }
    .file-input-label:hover {
      background: rgba(255,255,255,0.3);
      border-color: rgba(255,255,255,0.8);
    }
    .upload-btn {
      padding: 12px 20px;
      background: white;
      color: #667eea;
      border: none;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.3s;
      font-size: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }
    .upload-btn:hover:not(:disabled) {
      background: #f0f0f0;
      transform: translateY(-1px);
    }
    .upload-btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    .spinner {
      display: inline-block;
      width: 16px;
      height: 16px;
      border: 2px solid rgba(102, 126, 234, 0.3);
      border-radius: 50%;
      border-top-color: #667eea;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    .audio-item {
      padding: 12px 14px;
      border-radius: 10px;
      cursor: pointer;
      margin-bottom: 8px;
      background: #f9fafb;
      transition: all 0.2s;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }
    .audio-item:hover {
      background: #eef2ff;
      transform: translateX(4px);
    }
    .audio-item.active {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      font-weight: 500;
    }
    .audio-name {
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: 14px;
    }
    .delete-btn {
      padding: 4px 8px;
      background: rgba(239, 68, 68, 0.1);
      color: #dc2626;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      transition: all 0.2s;
      opacity: 0;
    }
    .audio-item:hover .delete-btn {
      opacity: 1;
    }
    .audio-item.active .delete-btn {
      background: rgba(255, 255, 255, 0.2);
      color: white;
      opacity: 1;
    }
    .delete-btn:hover {
      background: #dc2626;
      color: white;
    }
    section {
      background: rgba(255, 255, 255, 0.98);
      border-radius: 16px;
      padding: 32px;
      overflow-y: auto;
      box-shadow: 0 8px 32px rgba(0,0,0,0.12);
    }
    .player-section {
      position: sticky;
      top: 0;
      background: rgba(255, 255, 255, 0.98);
      padding-bottom: 24px;
      margin-bottom: 24px;
      border-bottom: 2px solid #e5e7eb;
      z-index: 10;
    }
    audio {
      width: 100%;
      margin: 0;
      border-radius: 12px;
      outline: none;
    }
    audio::-webkit-media-controls-panel {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    #transcript {
      line-height: 2.2;
      font-size: 16px;
      color: #374151;
    }
    .segment {
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 6px;
      transition: all 0.2s;
      display: inline;
      margin-right: 2px;
    }
    .segment:hover {
      background: #e0e7ff;
    }
    .segment.active {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      font-weight: 500;
    }
    .segment.playing {
      background: #fbbf24;
      color: #78350f;
      font-weight: 500;
    }
    .empty-state {
      text-align: center;
      padding: 60px 20px;
      color: #9ca3af;
    }
    .empty-state-icon {
      font-size: 64px;
      margin-bottom: 16px;
    }
    /* Modal styles */
    .modal {
      display: none;
      position: fixed;
      z-index: 1000;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0,0,0,0.5);
      animation: fadeIn 0.3s;
    }
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    .modal-content {
      background-color: white;
      margin: 15% auto;
      padding: 32px;
      border-radius: 16px;
      width: 90%;
      max-width: 400px;
      text-align: center;
      box-shadow: 0 20px 60px rgba(0,0,0,0.3);
      animation: slideUp 0.3s;
    }
    @keyframes slideUp {
      from {
        transform: translateY(50px);
        opacity: 0;
      }
      to {
        transform: translateY(0);
        opacity: 1;
      }
    }
    .modal-icon {
      font-size: 48px;
      margin-bottom: 16px;
    }
    .modal-title {
      font-size: 20px;
      font-weight: 600;
      margin-bottom: 8px;
      color: #1f2937;
    }
    .modal-text {
      color: #6b7280;
      margin-bottom: 24px;
    }
    .modal-btn {
      padding: 12px 32px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border: none;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.3s;
    }
    .modal-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    .confirm-modal .modal-content {
      max-width: 360px;
    }
    .confirm-buttons {
      display: flex;
      gap: 12px;
      justify-content: center;
    }
    .confirm-btn {
      padding: 10px 24px;
      border: none;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.3s;
    }
    .confirm-btn.cancel {
      background: #e5e7eb;
      color: #374151;
    }
    .confirm-btn.delete {
      background: #dc2626;
      color: white;
    }
    .confirm-btn:hover {
      transform: translateY(-1px);
    }
    /* Scrollbar styling */
    ::-webkit-scrollbar {
      width: 8px;
    }
    ::-webkit-scrollbar-track {
      background: #f1f1f1;
      border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb {
      background: #667eea;
      border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #764ba2;
    }
  </style>
</head>
<body>
<header>Japanese Listening Practice</header>
<main>
  <aside>
    <div class="upload-section">
      <h3 style="color: white; margin-bottom: 12px;">📤 Upload Audio</h3>
      <div class="upload-controls">
        <div class="file-input-wrapper">
          <input type="file" id="file" accept="audio/*" />
          <label for="file" class="file-input-label" id="fileLabel">
            Choose Audio File
          </label>
        </div>
        <button class="upload-btn" id="uploadBtn" onclick="upload()">
          <span id="uploadText">Start Transcription</span>
        </button>
      </div>
    </div>
    <h3>📚 Your Library</h3>
    <div id="library"></div>
  </aside>
  <section>
    <div class="player-section">
      <audio id="audio" controls></audio>
    </div>
    <div id="transcript">
      <div class="empty-state">
        <div class="empty-state-icon">🎵</div>
        <div>Select an audio file to view transcription</div>
      </div>
    </div>
  </section>
</main>

<!-- Success Modal -->
<div id="successModal" class="modal">
  <div class="modal-content">
    <div class="modal-icon">✅</div>
    <div class="modal-title">Transcription Complete!</div>
    <div class="modal-text">Your audio has been successfully transcribed.</div>
    <button class="modal-btn" onclick="closeModal()">Got it</button>
  </div>
</div>

<!-- Confirm Delete Modal -->
<div id="confirmModal" class="modal confirm-modal">
  <div class="modal-content">
    <div class="modal-icon">⚠️</div>
    <div class="modal-title">Delete Audio?</div>
    <div class="modal-text">This action cannot be undone.</div>
    <div class="confirm-buttons">
      <button class="confirm-btn cancel" onclick="closeConfirmModal()">Cancel</button>
      <button class="confirm-btn delete" onclick="confirmDelete()">Delete</button>
    </div>
  </div>
</div>

<script>
let currentAudioId = null;
let deleteAudioId = null;
const audio = document.getElementById('audio');
const uploadBtn = document.getElementById('uploadBtn');
const fileInput = document.getElementById('file');
const fileLabel = document.getElementById('fileLabel');
const uploadText = document.getElementById('uploadText');

// Update file label when file is selected
fileInput.addEventListener('change', (e) => {
  if (e.target.files.length > 0) {
    fileLabel.textContent = e.target.files[0].name;
  } else {
    fileLabel.textContent = 'Choose Audio File';
  }
});

async function loadLibrary() {
  const res = await fetch('/library');
  const data = await res.json();
  const lib = document.getElementById('library');
  
  if (data.length === 0) {
    lib.innerHTML = '<div style="text-align: center; padding: 20px; color: #9ca3af;">No audio files yet</div>';
    return;
  }
  
  lib.innerHTML = '';
  data.forEach(item => {
    const div = document.createElement('div');
    div.className = 'audio-item';
    
    const nameSpan = document.createElement('span');
    nameSpan.className = 'audio-name';
    nameSpan.innerText = item.original_name;
    nameSpan.onclick = () => loadAudio(item.id, div);
    
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'delete-btn';
    deleteBtn.innerText = '🗑️';
    deleteBtn.onclick = (e) => {
      e.stopPropagation();
      showDeleteConfirm(item.id);
    };
    
    div.appendChild(nameSpan);
    div.appendChild(deleteBtn);
    lib.appendChild(div);
  });
}

async function upload() {
  const file = fileInput.files[0];
  if (!file) {
    alert('Please select a file first');
    return;
  }
  
  // Disable upload controls
  uploadBtn.disabled = true;
  fileInput.disabled = true;
  uploadText.innerHTML = '<span class="spinner"></span> Transcribing...';
  
  try {
    const form = new FormData();
    form.append('file', file);
    await fetch('/transcribe', { method: 'POST', body: form });
    
    // Reset and show success
    fileInput.value = '';
    fileLabel.textContent = 'Choose Audio File';
    showSuccessModal();
    loadLibrary();
  } catch (error) {
    alert('Upload failed. Please try again.');
  } finally {
    // Re-enable upload controls
    uploadBtn.disabled = false;
    fileInput.disabled = false;
    uploadText.textContent = 'Start Transcription';
  }
}

async function loadAudio(id, element) {
  document.querySelectorAll('.audio-item').forEach(e => e.classList.remove('active'));
  element.classList.add('active');
  currentAudioId = id;

  const res = await fetch(`/audio_data/${id}`);
  const data = await res.json();
  audio.src = data.audio_url;

  const t = document.getElementById('transcript');
  t.innerHTML = '';
  
  data.segments.forEach((s, i) => {
    const span = document.createElement('span');
    span.className = 'segment';
    span.dataset.start = s.start;
    span.dataset.end = s.end;
    span.innerText = s.text.trim();
    span.onclick = () => {
      audio.currentTime = s.start;
      audio.play();
      document.querySelectorAll('.segment').forEach(e => e.classList.remove('active'));
      span.classList.add('active');
    };
    t.appendChild(span);
    
    // Add line break after each segment for better readability
    if (i < data.segments.length - 1) {
      t.appendChild(document.createElement('br'));
    }
  });
}

// Highlight current segment while playing
audio.addEventListener('timeupdate', () => {
  const currentTime = audio.currentTime;
  const segments = document.querySelectorAll('.segment');
  
  segments.forEach(segment => {
    const start = parseFloat(segment.dataset.start);
    const end = parseFloat(segment.dataset.end);
    
    if (currentTime >= start && currentTime <= end) {
      segment.classList.add('playing');
    } else {
      segment.classList.remove('playing');
    }
  });
});

function showSuccessModal() {
  document.getElementById('successModal').style.display = 'block';
}

function closeModal() {
  document.getElementById('successModal').style.display = 'none';
}

function showDeleteConfirm(audioId) {
  deleteAudioId = audioId;
  document.getElementById('confirmModal').style.display = 'block';
}

function closeConfirmModal() {
  document.getElementById('confirmModal').style.display = 'none';
  deleteAudioId = null;
}

async function confirmDelete() {
  if (!deleteAudioId) return;
  
  try {
    await fetch(`/delete/${deleteAudioId}`, { method: 'DELETE' });
    
    if (currentAudioId === deleteAudioId) {
      audio.src = '';
      document.getElementById('transcript').innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🎵</div>
          <div>Select an audio file to view transcription</div>
        </div>
      `;
      currentAudioId = null;
    }
    
    loadLibrary();
  } catch (error) {
    alert('Delete failed. Please try again.');
  }
  
  closeConfirmModal();
}

// Close modals when clicking outside
window.onclick = (event) => {
  const successModal = document.getElementById('successModal');
  const confirmModal = document.getElementById('confirmModal');
  if (event.target == successModal) {
    closeModal();
  }
  if (event.target == confirmModal) {
    closeConfirmModal();
  }
}

loadLibrary();
</script>
</body>
</html>
"""

# ----------------------
# API
# ----------------------
@app.post("/transcribe")
def transcribe(file: UploadFile = File(...)):
    audio_id = str(uuid.uuid4())
    filename = audio_id + "_" + file.filename
    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as f:
        f.write(file.file.read())

    # Use configured language for transcription
    result = model.transcribe(path, language=config['language'])

    cursor.execute("INSERT INTO audio VALUES (?, ?, ?)", (audio_id, filename, file.filename))
    for s in result['segments']:
        cursor.execute(
            "INSERT INTO segments VALUES (?, ?, ?, ?)",
            (audio_id, s['start'], s['end'], s['text'])
        )
    conn.commit()

    return {"status": "ok"}

@app.get("/library")
def library():
    cursor.execute("SELECT id, original_name FROM audio")
    return [{"id": r[0], "original_name": r[1]} for r in cursor.fetchall()]

@app.get("/audio_data/{audio_id}")
def audio_data(audio_id: str):
    cursor.execute("SELECT filename FROM audio WHERE id=?", (audio_id,))
    filename = cursor.fetchone()[0]
    cursor.execute("SELECT start, end, text FROM segments WHERE audio_id=?", (audio_id,))
    segments = [
        {"start": r[0], "end": r[1], "text": r[2]} for r in cursor.fetchall()
    ]
    return {
        "audio_url": f"/audio/{filename}",
        "segments": segments
    }

@app.delete("/delete/{audio_id}")
def delete_audio(audio_id: str):
    # Get filename to delete the file
    cursor.execute("SELECT filename FROM audio WHERE id=?", (audio_id,))
    result = cursor.fetchone()
    if result:
        filename = result[0]
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        # Delete the file if it exists
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Delete from database
        cursor.execute("DELETE FROM segments WHERE audio_id=?", (audio_id,))
        cursor.execute("DELETE FROM audio WHERE id=?", (audio_id,))
        conn.commit()
        
        return {"status": "deleted"}
    
    return {"status": "not_found"}

@app.get("/audio/{filename}")
def get_audio(filename: str):
    return FileResponse(os.path.join(UPLOAD_DIR, filename))

# Run: uvicorn app:app --reload