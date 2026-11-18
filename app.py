import asyncio
import io
import edge_tts
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

# Bộ nhớ đệm danh sách giọng nói để tải nhanh
CACHED_VOICES = None

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Chuyển Văn Bản Thành Giọng Nói & Tải MP3</title>
  <style>
    :root {
      --primary: #4f46e5;
      --primary-hover: #4338ca;
      --success: #059669;
      --success-hover: #047857;
      --bg: #f1f5f9;
      --card: #ffffff;
      --text: #0f172a;
      --muted: #64748b;
      --border: #e2e8f0;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: linear-gradient(135deg, #e0e7ff 0%, #f1f5f9 50%, #d1fae5 100%);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 20px;
    }

    .container {
      width: 100%;
      max-width: 820px;
      background: var(--card);
      border-radius: 20px;
      box-shadow: 0 20px 40px -15px rgba(15, 23, 42, 0.12);
      padding: 28px;
    }

    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 20px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }

    header h1 {
      font-size: 1.45rem;
      font-weight: 700;
    }

    header p {
      font-size: 0.88rem;
      color: var(--muted);
      margin-top: 4px;
    }

    .badge {
      padding: 6px 12px;
      border-radius: 999px;
      font-size: 0.82rem;
      font-weight: 600;
      background: #ecfdf5;
      color: #065f46;
      border: 1px solid #a7f3d0;
    }

    .textarea-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 8px;
    }

    .textarea-header label {
      font-weight: 600;
      font-size: 0.95rem;
    }

    .quick-actions { display: flex; gap: 6px; flex-wrap: wrap; }

    .btn-chip {
      background: #f1f5f9;
      border: 1px solid var(--border);
      color: #334155;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.8rem;
      cursor: pointer;
    }
    .btn-chip:hover { background: #e2e8f0; }

    textarea {
      width: 100%;
      min-height: 150px;
      padding: 14px;
      border: 1.5px solid var(--border);
      border-radius: 12px;
      font-family: inherit;
      font-size: 1rem;
      line-height: 1.6;
      resize: vertical;
      color: var(--text);
    }

    textarea:focus {
      outline: none;
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
    }

    .text-meta {
      display: flex;
      justify-content: space-between;
      margin-top: 6px;
      font-size: 0.82rem;
      color: var(--muted);
    }

    .settings-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-top: 20px;
      padding: 18px;
      background: #f8fafc;
      border-radius: 14px;
      border: 1px solid var(--border);
    }

    .full-width { grid-column: 1 / -1; }

    .control-group label {
      display: flex;
      justify-content: space-between;
      font-size: 0.88rem;
      font-weight: 600;
      margin-bottom: 8px;
      color: #334155;
    }

    .control-group label span.val {
      color: var(--primary);
      font-weight: 700;
    }

    select {
      width: 100%;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1.5px solid var(--border);
      background: #fff;
      font-size: 0.92rem;
      color: var(--text);
    }

    input[type="range"] {
      width: 100%;
      accent-color: var(--primary);
      cursor: pointer;
    }

    .presets { display: flex; gap: 8px; flex-wrap: wrap; }

    .preset-btn {
      padding: 7px 12px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: #fff;
      font-size: 0.84rem;
      font-weight: 500;
      cursor: pointer;
      color: #334155;
    }

    .preset-btn:hover { border-color: var(--primary); color: var(--primary); }
    .preset-btn.active {
      background: var(--primary);
      color: #fff;
      border-color: var(--primary);
    }

    .actions {
      display: flex;
      gap: 12px;
      margin-top: 20px;
      flex-wrap: wrap;
    }

    .btn {
      flex: 1;
      min-width: 180px;
      padding: 14px 20px;
      border: none;
      border-radius: 12px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      justify-content: center;
      align-items: center;
      gap: 8px;
      transition: transform 0.1s, opacity 0.2s, background-color 0.2s;
    }

    .btn:active:not(:disabled) { transform: scale(0.98); }
    .btn:disabled { opacity: 0.6; cursor: wait; }

    .btn-primary { background: var(--primary); color: #fff; }
    .btn-primary:hover:not(:disabled) { background: var(--primary-hover); }

    .btn-success { background: var(--success); color: #fff; }
    .btn-success:hover:not(:disabled) { background: var(--success-hover); }

    .player-box {
      display: none;
      margin-top: 18px;
      padding: 14px;
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 12px;
    }

    .player-box.active { display: block; }

    .player-box p {
      font-size: 0.85rem;
      font-weight: 600;
      color: #334155;
      margin-bottom: 8px;
    }

    audio {
      width: 100%;
      height: 40px;
    }

    .error-box {
      display: none;
      margin-top: 14px;
      padding: 12px;
      background: #fef2f2;
      color: #b91c1c;
      border: 1px solid #fecaca;
      border-radius: 10px;
      font-size: 0.9rem;
    }

    @media (max-width: 640px) {
      .container { padding: 18px; }
      .settings-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>🔊 Tạo Giọng Nói AI & Tải MP3</h1>
        <p>Sử dụng giọng đọc Neural tự nhiên, nghe thử và xuất file MP3 chất lượng cao</p>
      </div>
      <span class="badge">✨ Hỗ trợ tải MP3</span>
    </header>

    <div class="textarea-header">
      <label for="textInput">Nội dung văn bản</label>
      <div class="quick-actions">
        <button type="button" class="btn-chip" id="sampleViBtn">Mẫu Tiếng Việt</button>
        <button type="button" class="btn-chip" id="sampleEnBtn">Mẫu Tiếng Anh</button>
        <button type="button" class="btn-chip" id="clearBtn">Xóa hết</button>
      </div>
    </div>

    <textarea id="textInput" placeholder="Nhập văn bản bạn muốn chuyển thành file MP3...">Xin chào! Chào mừng bạn đến với ứng dụng chuyển văn bản thành giọng nói. Bạn có thể nghe thử trực tiếp hoặc nhấn nút tải xuống để lưu thành file MP3 về máy.</textarea>

    <div class="text-meta">
      <span id="charCount">0 ký tự • 0 từ</span>
    </div>

    <div class="settings-grid">
      <div class="control-group full-width">
        <label for="voiceSelect">
          <span>🗣️ Chọn giọng nói</span>
          <span class="val" id="voiceCountLabel">Đang tải...</span>
        </label>
        <select id="voiceSelect">
          <option value="vi-VN-HoaiMyNeural">🇻🇳 HoaiMy - Nữ (vi-VN-HoaiMyNeural)</option>
          <option value="vi-VN-NamMinhNeural">🇻🇳 NamMinh - Nam (vi-VN-NamMinhNeural)</option>
        </select>
      </div>

      <div class="control-group full-width">
        <label><span>🎭 Kiểu giọng cài sẵn (Presets)</span></label>
        <div class="presets">
          <button type="button" class="preset-btn active" data-rate="0" data-pitch="0">Tự nhiên</button>
          <button type="button" class="preset-btn" data-rate="-12" data-pitch="-15">Trầm ấm (Kể chuyện)</button>
          <button type="button" class="preset-btn" data-rate="15" data-pitch="15">Vui tươi (Năng động)</button>
          <button type="button" class="preset-btn" data-rate="-25" data-pitch="0">Chậm rãi (Rõ ràng)</button>
          <button type="button" class="preset-btn" data-rate="0" data-pitch="-30">Giọng trầm sâu</button>
        </div>
      </div>

      <div class="control-group">
        <label for="rateRange">
          <span>⚡ Tốc độ đọc</span>
          <span class="val" id="rateVal">+0%</span>
        </label>
        <input type="range" id="rateRange" min="-50" max="100" step="5" value="0" />
      </div>

      <div class="control-group">
        <label for="pitchRange">
          <span>🎵 Cao độ (Trầm / Bổng)</span>
          <span class="val" id="pitchVal">+0Hz</span>
        </label>
        <input type="range" id="pitchRange" min="-50" max="50" step="5" value="0" />
      </div>

      <div class="control-group full-width">
        <label for="volumeRange">
          <span>🔉 Âm lượng</span>
          <span class="val" id="volumeVal">+0%</span>
        </label>
        <input type="range" id="volumeRange" min="-50" max="50" step="5" value="0" />
      </div>
    </div>

    <div class="actions">
      <button type="button" id="playBtn" class="btn btn-primary">▶ Tạo & Nghe thử</button>
      <button type="button" id="downloadBtn" class="btn btn-success">⬇ Tải xuống MP3</button>
    </div>

    <div id="errorBox" class="error-box"></div>

    <div id="playerBox" class="player-box">
      <p>🎧 Trình phát âm thanh:</p>
      <audio id="audioPlayer" controls></audio>
    </div>
  </div>

  <script>
    const textInput = document.getElementById('textInput');
    const charCount = document.getElementById('charCount');
    const voiceSelect = document.getElementById('voiceSelect');
    const voiceCountLabel = document.getElementById('voiceCountLabel');
    const rateRange = document.getElementById('rateRange');
    const pitchRange = document.getElementById('pitchRange');
    const volumeRange = document.getElementById('volumeRange');
    const rateVal = document.getElementById('rateVal');
    const pitchVal = document.getElementById('pitchVal');
    const volumeVal = document.getElementById('volumeVal');
    const playBtn = document.getElementById('playBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const playerBox = document.getElementById('playerBox');
    const audioPlayer = document.getElementById('audioPlayer');
    const errorBox = document.getElementById('errorBox');
    const presetBtns = document.querySelectorAll('.preset-btn');

    let lastRequestKey = null;
    let cachedBlob = null;
    let cachedUrl = null;

    function updateMeta() {
      const val = textInput.value.trim();
      const words = val ? val.split(/\s+/).length : 0;
      charCount.textContent = `${textInput.value.length} ký tự • ${words} từ`;
    }
    textInput.addEventListener('input', updateMeta);
    updateMeta();

    document.getElementById('sampleViBtn').addEventListener('click', () => {
      textInput.value = "Công nghệ tổng hợp giọng nói AI ngày nay giúp chuyển đổi văn bản thành âm thanh tự nhiên như người thật. Bạn có thể tạo sách nói, video thuyết minh và tải file MP3 về máy chỉ với một cú nhấp chuột.";
      updateMeta();
    });

    document.getElementById('sampleEnBtn').addEventListener('click', () => {
      textInput.value = "Hello! Welcome to this Text-to-Speech application. You can choose from natural neural voices, preview the audio directly, and download it as an MP3 file.";
      updateMeta();
    });

    document.getElementById('clearBtn').addEventListener('click', () => {
      textInput.value = '';
      updateMeta();
      textInput.focus();
    });

    function formatSigned(num, unit) {
      const n = parseInt(num, 10);
      return `${n >= 0 ? '+' : ''}${n}${unit}`;
    }

    function syncLabels() {
      rateVal.textContent = formatSigned(rateRange.value, '%');
      pitchVal.textContent = formatSigned(pitchRange.value, 'Hz');
      volumeVal.textContent = formatSigned(volumeRange.value, '%');
    }

    [rateRange, pitchRange, volumeRange].forEach(el => {
      el.addEventListener('input', () => {
        syncLabels();
        if (el !== volumeRange) {
          presetBtns.forEach(b => b.classList.remove('active'));
        }
      });
    });

    presetBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        presetBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        rateRange.value = btn.dataset.rate;
        pitchRange.value = btn.dataset.pitch;
        syncLabels();
      });
    });

    // Tải danh sách giọng nói từ backend
    async function loadVoices() {
      try {
        const res = await fetch('/api/voices');
        if (!res.ok) throw new Error('Không tải được danh sách giọng');
        const voices = await res.json();

        voiceSelect.innerHTML = '';
        voices.forEach(v => {
          const opt = document.createElement('option');
          opt.value = v.ShortName;
          const flag = v.Locale.toLowerCase().startsWith('vi') ? '🇻🇳 ' : '';
          const gender = v.Gender === 'Female' ? 'Nữ' : 'Nam';
          opt.textContent = `${flag}${v.LocalName} (${gender} - ${v.Locale})`;
          voiceSelect.appendChild(opt);
        });

        voiceCountLabel.textContent = `${voices.length} giọng Neural`;
      } catch (err) {
        voiceCountLabel.textContent = 'Dùng giọng mặc định';
      }
    }
    loadVoices();

    function showError(msg) {
      errorBox.textContent = msg;
      errorBox.style.display = 'block';
    }

    function hideError() {
      errorBox.style.display = 'none';
    }

    function setLoading(isLoading) {
      playBtn.disabled = isLoading;
      downloadBtn.disabled = isLoading;
      playBtn.textContent = isLoading ? '⏳ Đang tạo âm thanh...' : '▶ Tạo & Nghe thử';
      downloadBtn.textContent = isLoading ? '⏳ Đang xử lý...' : '⬇ Tải xuống MP3';
    }

    async function generateAudioBlob() {
      const payload = {
        text: textInput.value.trim(),
        voice: voiceSelect.value,
        rate: parseInt(rateRange.value, 10),
        pitch: parseInt(pitchRange.value, 10),
        volume: parseInt(volumeRange.value, 10),
      };

      if (!payload.text) {
        alert('Vui lòng nhập văn bản trước!');
        textInput.focus();
        return null;
      }

      const currentKey = JSON.stringify(payload);
      if (currentKey === lastRequestKey && cachedBlob) {
        return cachedBlob;
      }

      hideError();
      setLoading(true);

      try {
        const res = await fetch('/api/tts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.error || 'Lỗi khi tạo file MP3.');
        }

        const blob = await res.blob();
        if (cachedUrl) URL.revokeObjectURL(cachedUrl);
        cachedBlob = blob;
        cachedUrl = URL.createObjectURL(blob);
        lastRequestKey = currentKey;

        audioPlayer.src = cachedUrl;
        playerBox.classList.add('active');
        return blob;
      } catch (err) {
        showError('⚠️ ' + err.message);
        return null;
      } finally {
        setLoading(false);
      }
    }

    playBtn.addEventListener('click', async () => {
      const blob = await generateAudioBlob();
      if (blob) {
        audioPlayer.play();
      }
    });

    downloadBtn.addEventListener('click', async () => {
      const blob = await generateAudioBlob();
      if (!blob) return;

      const a = document.createElement('a');
      a.href = cachedUrl;
      a.download = `giong-noi-${Date.now()}.mp3`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    });
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return HTML_PAGE


@app.route("/api/voices", methods=["GET"])
def get_voices():
    global CACHED_VOICES
    if CACHED_VOICES is None:
        raw_voices = asyncio.run(edge_tts.list_voices())
        # Đưa giọng Tiếng Việt lên đầu, sau đó Tiếng Anh, rồi các ngôn ngữ khác
        raw_voices.sort(
            key=lambda v: (
                0 if v["Locale"].lower().startswith("vi") else (1 if v["Locale"].lower().startswith("en") else 2),
                v["Locale"],
                v["ShortName"],
            )
        )
        CACHED_VOICES = [
            {
                "ShortName": v["ShortName"],
                "Locale": v["Locale"],
                "Gender": v["Gender"],
                "LocalName": v["ShortName"].replace(v["Locale"] + "-", "").replace("Neural", ""),
            }
            for v in raw_voices
        ]
    return jsonify(CACHED_VOICES)


async def synthesize_mp3_bytes(text: str, voice: str, rate: int, pitch: int, volume: int) -> bytes:
    rate_str = f"{rate:+d}%"
    pitch_str = f"{pitch:+d}Hz"
    volume_str = f"{volume:+d}%"

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate_str,
        pitch=pitch_str,
        volume=volume_str,
    )

    audio_buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])

    audio_bytes = audio_buffer.getvalue()
    if not audio_bytes:
        raise RuntimeError("Không nhận được dữ liệu âm thanh từ máy chủ TTS.")
    return audio_bytes


@app.route("/api/tts", methods=["POST"])
def text_to_speech():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    voice = data.get("voice") or "vi-VN-HoaiMyNeural"
    rate = int(data.get("rate", 0))
    pitch = int(data.get("pitch", 0))
    volume = int(data.get("volume", 0))

    if not text:
        return jsonify({"error": "Văn bản không được để trống."}), 400

    try:
        mp3_bytes = asyncio.run(synthesize_mp3_bytes(text, voice, rate, pitch, volume))
        return send_file(
            io.BytesIO(mp3_bytes),
            mimetype="audio/mpeg",
            as_attachment=False,
            download_name="giong-noi.mp3",
        )
    except Exception as e:
        return jsonify({"error": f"Không thể tạo âm thanh (kiểm tra kết nối mạng): {str(e)}"}), 500


import socket

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    lan_ip = get_lan_ip()
    print("--------------------------------------------------")
    print(f"Mở trên máy này:            http://127.0.0.1:5000")
    print(f"Mở trên máy khác cùng WiFi: http://{lan_ip}:5000")
    print("--------------------------------------------------")
    app.run(host="0.0.0.0", port=5000, debug=False)