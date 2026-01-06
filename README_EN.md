# RogoAI Voice Studio v2.4

![Version](https://img.shields.io/badge/version-2.4-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

## 🌐 Language / 言語

- [日本語版 README](README_JP.md)
- [English README](README_EN.md) ← Current page

---

**Easy-to-Use AI Voice Synthesis Studio for Seniors**

An integrated voice synthesis application combining VOICEVOX, Coqui TTS, and faster-whisper, designed for senior-friendly usability.

---

## ✨ Key Features

### 🎤 Voice Synthesis
- **VOICEVOX**: High-quality Japanese voice synthesis
- **Coqui TTS**: Multi-language voice synthesis engine
- Emotion expression, speed, and pitch adjustment

### 📝 Whisper Transcription (v2.1+)
- Automatic transcription from MP4 videos
- 3 accuracy model options (base/medium/large-v3)
- 95% high accuracy (medium model)

### 📊 Daily Logger (v2.0+)
- Auto-save logs in same folder as audio files
- Completion notification
- Timestamped log files

---

## 📦 Download

### ⚡ EXE Version (Recommended for Beginners)

**EXE version is recommended for v2.4+** - No Python environment required, download and use immediately!

#### 📥 [Download Latest Release](https://github.com/RogoAI-Takeji/Voice-Studio/releases/latest)

- **日本語版**: `rogoai_voice_studio_v2.4_JP.zip`
- **English Version**: `rogoai_voice_studio_v2.4_EN.zip`

### 🐍 Python Version (For Advanced Users)

If you have a Python environment, you can run from source code.

```bash
git clone https://github.com/RogoAI-Takeji/Voice-Studio.git
cd Voice-Studio/src
```

---

## 🚀 Installation (EXE Version)

### Step 1: Download
1. Download the latest ZIP file from [Releases](https://github.com/RogoAI-Takeji/Voice-Studio/releases)
2. Select `rogoai_voice_studio_v2.4_EN.zip` for English version

### Step 2: Extract
1. Right-click the downloaded ZIP file
2. Select "Extract All"
3. Extract to your preferred location (e.g., Desktop, Documents)

### Step 3: Run
1. Open the extracted folder
2. Double-click `rogoai_voice_studio_v2.4_EN.exe`
3. The app will launch!

### ⚠️ Important Notes

**NEVER delete or move the `_internal` folder!**

```
RogoAI_Voice_Studio_EN/  ← Keep this entire folder
├── rogoai_voice_studio_v2.4_EN.exe  ← Launch this
└── _internal/  ← NEVER touch this!
```

#### To Place Icon on Desktop
1. Right-click the EXE file
2. Select "Create shortcut"
3. Move the created shortcut to Desktop

**Warning**: Moving the EXE file itself will break the application!

---

## 📖 How to Use

### Basic Usage

#### 1. Voice Synthesis (VOICEVOX)
1. Enter text in the text box
2. Select VOICEVOX character and emotion
3. Adjust speed and pitch (optional)
4. Click "Generate Voice" button
5. Specify save location and complete

#### 2. Voice Synthesis (Coqui TTS)
1. Enter text in the text box
2. Select Coqui TTS model
3. Adjust speed (optional)
4. Click "Generate Voice" button
5. Specify save location and complete

#### 3. Whisper Transcription (v2.1+)
1. Open "Whisper" tab
2. Select MP4 video file
3. Choose model size:
   - **base**: Fast (2-3 min for 10-min video)
   - **medium**: High accuracy, recommended (5-7 min for 10-min video)
   - **large-v3**: Highest accuracy (10-15 min for 10-min video)
4. Click "Start Transcription" button
5. SRT file will be saved in the same folder as the video

### 📋 Detailed Instructions

For more detailed usage, see [docs/how_to_use.md](docs/how_to_use_EN.md).

---

## 🔧 Troubleshooting

### EXE Won't Launch

#### Cause 1: `_internal` folder is missing
- **Solution**: Re-download the ZIP file and extract correctly

#### Cause 2: Security software is blocking
- **Solution**: Configure your security software to allow this app

#### Cause 3: Windows Defender warning
- **Solution**: 
  1. Click "More info"
  2. Click "Run anyway"
  3. This is a standard warning for unsigned apps

### VOICEVOX Engine Not Found

#### VOICEVOX not installed
- **Solution**: Download and install from [VOICEVOX Official Site](https://voicevox.hiroshiba.jp/)

#### VOICEVOX not running
- **Solution**: Launch VOICEVOX before using Voice Studio

### Whisper Processing is Slow

#### Cause: Using large-v3 model
- **Solution**: Switch to medium model (95% accuracy, practically sufficient)

### Can't Find Log Files

#### v2.0+ Behavior
- **Location**: Same folder as audio files
- **Filename**: `voice_studio_log_YYYYMMDD_HHMMSS.txt`

---

## 🛠️ Python Version Installation (For Advanced Users)

### Requirements
- Python 3.10 or higher
- pip (Python package manager)
- ffmpeg, ffprobe (for audio processing)

### Installation Steps

```bash
# Clone repository
git clone https://github.com/RogoAI-Takeji/Voice-Studio.git
cd Voice-Studio

# Install required packages
pip install -r requirements.txt

# Launch app (Japanese version)
cd src
python rogoai_voice_studio_v2_4_JP.py

# Or English version
python rogoai_voice_studio_v2_4_EN.py
```

### Installing ffmpeg

#### Windows
1. Download from [ffmpeg official site](https://ffmpeg.org/download.html)
2. Place `ffmpeg.exe` and `ffprobe.exe` in `src/ffmpeg/` folder

#### Mac/Linux
```bash
# Mac (Homebrew)
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

---

## 📚 Documentation

- [Changelog](CHANGELOG_EN.md)
- [Detailed Usage Guide](docs/how_to_use_EN.md)
- [FAQ](docs/FAQ_EN.md)

---

## 🎬 Tutorial Videos

Check out our YouTube tutorials:

- [Voice Studio v2.4 Basic Operations](https://youtube.com/@RogoAI)
- [How to Use Whisper Transcription](https://youtube.com/@RogoAI)

---

## 🤝 Contributing

Pull requests and issue reports are welcome!

1. Fork this repository
2. Create a new branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Create a Pull Request

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [VOICEVOX](https://voicevox.hiroshiba.jp/) - High-quality Japanese voice synthesis
- [Coqui TTS](https://github.com/coqui-ai/TTS) - Open-source voice synthesis engine
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - Fast speech recognition
- [PyInstaller](https://pyinstaller.org/) - Python app to exe converter

---

## 📧 Contact

- **YouTube**: [老後AI (RogoAI)](https://youtube.com/@RogoAI)
- **GitHub Issues**: [Report Issues](https://github.com/RogoAI-Takeji/Voice-Studio/issues)

---

## ⭐ Star & Follow Us!

If this project helps you, please give us a star on GitHub!

[![Star on GitHub](https://img.shields.io/github/stars/RogoAI-Takeji/Voice-Studio.svg?style=social)](https://github.com/RogoAI-Takeji/Voice-Studio)

---

**Made with ❤️ by RogoAI-Takeji**

*Bringing AI development joy to seniors*
