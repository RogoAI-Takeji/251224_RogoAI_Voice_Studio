# Changelog

## 🌐 Language / 言語

- [日本語版 CHANGELOG](CHANGELOG_JP.md)
- [English CHANGELOG](CHANGELOG_EN.md) ← Current page

---

## [v2.4] - 2025-01-06

### ✨ New Features
- **EXE Build Complete**: PyInstaller executable packaging
  - Independent EXE files for JP/EN versions
  - Distributed with `_internal` folder (onedir mode)
  - Bundled with ffmpeg and ffprobe
  - All dependencies integrated (faster-whisper, TTS, torch, etc.)

### 🔧 Technical Improvements
- Optimized PyInstaller build scripts
- Added GGUF model support dependencies
- Optimized hidden-import configurations

### 📦 Distribution Method Changes
- **Important**: EXE file and `_internal` folder must be distributed together
- Provided as ZIP file containing the parent folder
- Users extract and run the EXE inside the folder

---

## [v2.3] - 2025-01-04

### ✨ New Features
- Stabilized Whisper transcription functionality
- Improved model selection UI
- Optimized processing speed

---

## [v2.2] - 2025-01-03

### ✨ New Features
- faster-whisper integration for high-speed transcription
- Three model size options (base/medium/large-v3)
- Default model set to base

### 🎯 Usability Improvements
- Implemented model selection UI
- Achieved 95% accuracy with medium model

---

## [v2.1] - 2025-01-02

### ✨ New Features
- **Whisper Transcription Feature Added** (Phase 2)
  - Automatic transcription from MP4 videos
  - faster-whisper engine integration
  - Selectable model sizes

---

## [v2.0] - 2025-01-01

### ✨ New Features
- **Daily Logger Feature** (Phase 1 Complete)
  - Auto-save log files in same folder as audio files
  - Display notification on completion
  - Both JP/EN versions supported

### 🎯 Usability Improvements
- Simplified file management (logs and audio in same location)
- Immediate user feedback display

---

## [v1.9.2] - 2024-12-25

### Final Slim Version
- VOICEVOX and Coqui TTS support
- Python environment execution
- Batch file setup
- Basic voice synthesis features

---

## Important Notes for EXE Distribution

### Distribution File Structure
```
RogoAI_Voice_Studio_EN/  ← ZIP this entire folder
├── rogoai_voice_studio_v2.4_EN.exe  ← Launch file
└── _internal/  ← Core files (NEVER delete or separate)
    ├── Python runtime
    ├── AI libraries (PyTorch, TTS, etc.)
    └── Dependent DLLs
```

### ⚠️ Warnings
1. **NEVER delete, move, or separate the `_internal` folder**
2. EXE file and `_internal` folder must be in the same directory
3. To place EXE on desktop, create a **shortcut** instead of moving the file

### 📋 Build Commands (For Developers)

#### JP Version
```bash
pyinstaller --noconfirm --onedir --windowed --clean \
  --name "rogoai_voice_studio_v2.4_JP" \
  --icon "make_icon/icon.ico" \
  --add-binary "ffmpeg/ffmpeg.exe;ffmpeg" \
  --add-binary "ffmpeg/ffprobe.exe;ffmpeg" \
  --add-data "make_icon/icon.ico;make_icon" \
  --collect-all TTS \
  --collect-all torch \
  --collect-all torchaudio \
  --collect-all scipy \
  --collect-all lazy_loader \
  --collect-all trainer \
  --collect-all gruut \
  --collect-all jamo \
  --collect-all unidic_lite \
  --collect-all cutlet \
  --collect-all faster_whisper \
  --hidden-import="scipy.special.cython_special" \
  --hidden-import="whisper_engine" \
  rogoai_voice_studio_v2_4_JP.py
```

#### EN Version
```bash
pyinstaller --noconfirm --onedir --windowed --clean \
  --name "rogoai_voice_studio_v2.4_EN" \
  --icon "make_icon/icon.ico" \
  --add-binary "ffmpeg/ffmpeg.exe;ffmpeg" \
  --add-binary "ffmpeg/ffprobe.exe;ffmpeg" \
  --add-data "make_icon/icon.ico;make_icon" \
  --collect-all TTS \
  --collect-all torch \
  --collect-all torchaudio \
  --collect-all scipy \
  --collect-all lazy_loader \
  --collect-all trainer \
  --collect-all gruut \
  --collect-all jamo \
  --collect-all unidic_lite \
  --collect-all cutlet \
  --collect-all faster_whisper \
  --hidden-import="scipy.special.cython_special" \
  --hidden-import="whisper_engine" \
  rogoai_voice_studio_v2_4_EN.py
```

---

## Version Numbering

- **Major**: Large feature additions or breaking changes (e.g., v1 → v2)
- **Minor**: New feature additions (e.g., v2.0 → v2.1)
- **Patch**: Bug fixes or minor improvements (e.g., v2.1 → v2.1.1)

---

## Release Notes

Detailed release notes for each version are available on [GitHub Releases](https://github.com/RogoAI-Takeji/Voice-Studio/releases).
