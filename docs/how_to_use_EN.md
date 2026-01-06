# RogoAI Voice Studio v2.4 Usage Guide

## 🌐 Language / 言語

- [日本語版マニュアル](how_to_use_JP.md)
- [English Manual](how_to_use_EN.md) ← Current page

---

This guide provides detailed instructions for using RogoAI Voice Studio.

---

## 📋 Table of Contents

1. [Getting Started](#getting-started)
2. [VOICEVOX Voice Synthesis](#voicevox-voice-synthesis)
3. [Coqui TTS Voice Synthesis](#coqui-tts-voice-synthesis)
4. [Whisper Transcription](#whisper-transcription)
5. [Settings and Customization](#settings-and-customization)
6. [Frequently Asked Questions](#frequently-asked-questions)

---

## Getting Started

### What is Voice Studio?

Voice Studio is an application that converts text to speech and transcribes audio from videos.

**Features:**
- 📖 Convert text to speech
- 🎭 Generate voices with various characters and emotions
- 🎬 Automatic transcription from video files
- 📝 Automatic subtitle file (SRT) creation

### Basic Interface

#### Screen Layout

```
┌─────────────────────────────────────────┐
│  Tabs  │ VOICEVOX │ Coqui │ Whisper    │
├─────────────────────────────────────────┤
│                                         │
│  【Text Input Area】                    │
│  Enter text to be read aloud here      │
│                                         │
├─────────────────────────────────────────┤
│  Character Selection ▼                  │
│  Emotion Selection ▼                    │
│  Speed Adjustment ━━●━━                 │
│  Pitch Adjustment ━━●━━                 │
├─────────────────────────────────────────┤
│      [Generate Voice Button]            │
└─────────────────────────────────────────┘
```

---

## VOICEVOX Voice Synthesis

### Step 1: Preparing VOICEVOX

Before using Voice Studio, you need to install and launch VOICEVOX.

#### Installing VOICEVOX (First Time Only)

1. Visit [VOICEVOX Official Site](https://voicevox.hiroshiba.jp/)
2. Click the "Download" button
3. Run the downloaded file to install
4. After installation, launch VOICEVOX

#### Confirming VOICEVOX is Running

Verify VOICEVOX is running properly:
- VOICEVOX icon appears in taskbar
- VOICEVOX window is open

### Step 2: Voice Generation

#### Basic Steps

1. **Tab Selection**: Click "VOICEVOX" tab
2. **Text Input**: Enter text to be read aloud
   ```
   Example: Hello. This is Take-jii from RogoAI.
   ```
3. **Character Selection**: Choose your preferred character
   - Zundamon
   - Shikoku Metan
   - Kasukabe Tsumugi
   - And many more
4. **Emotion Selection**: Select character's emotion
   - Normal
   - Happy
   - Angry
   - Sad
   - And more
5. **Generate Voice**: Click "Generate Voice" button
6. **Save**: Specify filename and save location

#### Advanced Settings

##### Speed Adjustment
- **Slider**: Move left or right to adjust
- **Range**: 0.5x to 2.0x speed
- **Recommended**: 
  - Slow: 0.8x
  - Normal: 1.0x
  - Fast: 1.3x

##### Pitch Adjustment
- **Slider**: Move left or right to adjust
- **Range**: -12 to +12 (semitones)
- **Recommended**: 
  - Low voice: -3 to -5
  - Normal: 0
  - High voice: +3 to +5

### Step 3: File Saving

#### Save Formats
- **WAV format**: Uncompressed, high quality
- **MP3 format**: Compressed, smaller file size

#### Recommended Filename Format

```
Example 1: 2025-01-06_intro_zundamon.wav
  ├─ Date
  ├─ Content description
  └─ Character name

Example 2: video01_narration_tsumugi.mp3
  ├─ Project name
  ├─ Purpose
  └─ Character name
```

---

## Coqui TTS Voice Synthesis

### Step 1: Model Selection

Coqui TTS is a multilingual voice synthesis engine.

#### Available Languages
- Japanese
- English
- Chinese
- Spanish
- And many more

### Step 2: Voice Generation

#### Basic Steps

1. **Tab Selection**: Click "Coqui TTS" tab
2. **Text Input**: Enter text to be read aloud
3. **Model Selection**: Select model matching your language
4. **Speed Adjustment**: Adjust to your preference
5. **Generate Voice**: Click "Generate Voice" button
6. **Save**: Specify filename and save location

#### Coqui TTS Characteristics

**Advantages:**
- Multilingual support
- No VOICEVOX installation required
- Works offline

**Disadvantages:**
- Less natural than VOICEVOX
- Lower Japanese accuracy than VOICEVOX

**Usage Guidelines:**
- Japanese voice → VOICEVOX recommended
- English voice → Coqui TTS recommended
- Mixed languages → Coqui TTS

---

## Whisper Transcription

### Overview

Whisper feature extracts audio from MP4 video files and converts it to text.

### Step 1: Preparing Video Files

#### Supported Formats
- MP4 (recommended)
- AVI
- MOV
- MKV

#### File Size Guidelines
- 10-minute video: approx. 50-200MB
- 30-minute video: approx. 150-600MB

### Step 2: Model Selection

#### Three Model Types

| Model | Speed | Accuracy | Recommended Use | Processing Time (10-min video) |
|-------|-------|----------|-----------------|--------------------------------|
| **base** | ⚡⚡⚡ | ★★☆ | Testing, drafts | 2-3 minutes |
| **medium** | ⚡⚡ | ★★★ | **Recommended** | 5-7 minutes |
| **large-v3** | ⚡ | ★★★★ | Highest accuracy | 10-15 minutes |

#### Selection Tips

**For Beginners:**
- Try **medium model** first
- 95% accuracy, practically sufficient

**Use base model when:**
- You need quick results
- Rough content check is enough
- Planning manual correction later

**Use large-v3 when:**
- Videos contain technical terms
- Multiple speakers
- Highest quality required

### Step 3: Running Transcription

#### Basic Steps

1. **Tab Selection**: Click "Whisper" tab
2. **File Selection**: Click "Select Video File" button
3. **Choose Video**: Select MP4 file
4. **Model Selection**: medium recommended
5. **Execute**: Click "Start Transcription" button
6. **Wait**: Monitor progress bar
7. **Complete**: SRT file is automatically saved

#### Progress Display

```
Processing...
━━━━━━━●━━━━━━━ 45%
Estimated remaining: 3 min 20 sec
```

### Step 4: Checking Results

#### Generated Files

**Original video:**
```
C:\Users\YourName\Videos\sample.mp4
```

**Generated SRT file:**
```
C:\Users\YourName\Videos\sample.srt
```

#### SRT File Content (Example)

```srt
1
00:00:00,000 --> 00:00:03,500
Hello. This is Take-jii from RogoAI.

2
00:00:03,500 --> 00:00:08,200
Today I'll explain how to use Whisper feature.

3
00:00:08,200 --> 00:00:12,800
With this feature, you can automatically create subtitles from videos.
```

### Step 5: Using Subtitles

#### In Video Editing Software

**DaVinci Resolve:**
1. Add subtitle track
2. Import SRT file
3. Place on timeline

**Adobe Premiere Pro:**
1. File → Import → SRT file
2. Drag to subtitle track

**Free Video Editors:**
- Shotcut (free)
- OpenShot (free)

#### YouTube Upload

1. Open YouTube Studio
2. Upload video
3. "Subtitles" → "Upload file"
4. Select SRT file

---

## Settings and Customization

### Changing Save Location

#### Setting Default Save Location

1. Open "Settings" menu
2. Select "Default Save Location"
3. Choose preferred folder
4. Click "Save" button

### Checking Log Files

#### Log File Location (v2.0+)

Automatically saved in same folder as audio files:
```
voice_studio_log_20250106_143052.txt
```

#### Log File Content

```
[2025-01-06 14:30:52] App launched
[2025-01-06 14:31:15] VOICEVOX voice generation started
[2025-01-06 14:31:22] Voice generation complete: sample.wav
[2025-01-06 14:32:10] Whisper transcription started: video.mp4
[2025-01-06 14:37:45] Transcription complete: video.srt
```

---

## Frequently Asked Questions

### Q1: "VOICEVOX not found" error appears

**A**: Is VOICEVOX running?
1. Launch VOICEVOX app
2. Restart Voice Studio
3. Try again

### Q2: Voice generation is slow

**A**: Check the following:
- Is PC memory sufficient? (8GB+ recommended)
- Try closing other apps
- If text is too long, try splitting it

### Q3: Whisper processing stops mid-way

**A**: Try these solutions:
1. Switch to base model
2. Split video file into shorter segments
3. Restart PC and try again

### Q4: Subtitle timing is off

**A**: This is a Whisper limitation:
- 95% accuracy with medium model
- Manual adjustment needed for perfection
- Adjust timing in video editing software

### Q5: App stopped working after moving EXE file

**A**: It's separated from `_internal` folder:
1. Return to original folder
2. Create shortcut and place on desktop
3. Don't move EXE file itself

### Q6: Windows Defender warning appears

**A**: Standard warning for unsigned apps:
1. Click "More info"
2. Click "Run anyway"
3. This is a safe application

### Q7: Japanese text appears garbled

**A**: Does filename contain special characters?
- Allowed in filenames:
  - Alphanumeric characters
  - Underscore (_)
  - Hyphen (-)
- Characters to avoid:
  - Spaces
  - Full-width characters (preferably)
  - Special symbols (<>:"/\|?*)

---

## 🎬 Video Tutorials

For more detailed instructions, check out our YouTube channel:

**RogoAI YouTube: https://youtube.com/@RogoAI**

- Voice Studio basic operations
- Whisper transcription tips
- Subtitle editing methods
- Troubleshooting

---

## 📧 Support

If problems persist:

1. **GitHub Issues**: [Report issue](https://github.com/RogoAI-Takeji/Voice-Studio/issues)
2. **YouTube**: Ask in comments section
3. **Log Files**: Check log files for errors

---

**Happy Voice Synthesis! 🎤**

*RogoAI Voice Studio Team*
