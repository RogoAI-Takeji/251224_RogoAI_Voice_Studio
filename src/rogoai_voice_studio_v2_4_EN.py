"""
ROGOAI Voice Studio v2.4 EN
Universal Voice Generation Platform

Features:
1. VOICEVOX Character Voice Generation
2. Coqui TTS XTTS Zero-Shot Voice Cloning
3. GUI Refresh: Slimmed down & Custom Filename Naming
4. Safe Asynchronous Startup Process
5. UI adjustments for JP/EN deployment
★6. Daily Logger: Auto-record text during voice generation
★7. Whisper Speech Recognition: High-speed transcription via faster-whisper
   - base/medium/large-v3 model selection
   - Text/SRT subtitle output formats
   - Transfer function to Voice Generation Tab
★8. Preset Management: Save/Load frequently used settings (v2.2)
★9. Voice Preview: Generate only the first 30 chars for testing (v2.2)
★10. Batch Processing: Process multiple files at once (v2.2)
★11. Text History: Save last 10 entries (v2.2)
★12. Template Function: Save/Load standard phrases (v2.2)
★13. Auto Backup: Auto-save during text input (v2.2)
★14. Sound Recorder: Record directly from mic -> Transcribe (v2.3)

Author: ROGOAI
Version: 2.4 EN (Explorer Edition)
License: MIT
"""

try:
    import pyi_splash
except ImportError:
    pass

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import requests
import json
import os
import sys
from pathlib import Path
import urllib.parse
import subprocess
import platform
from datetime import datetime
from pydub import AudioSegment
import io
import threading
import traceback
import time

# Recording Functionality (Added in v2.3)
try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    RECORDING_AVAILABLE = True
except ImportError:
    RECORDING_AVAILABLE = False
    print("⚠ Recording disabled: sounddevice or soundfile not installed")

# ==========================================
# EXE Support: Patch for 'could not get source code' error
# ==========================================
import inspect
import sys

if getattr(sys, 'frozen', False):
    def _safe_getsource(object):
        return ""
    inspect.getsource = _safe_getsource
# ==========================================


# ==========================================
# PyTorch Compatibility Patch
# ==========================================
import torch
_original_load = torch.load
def _patched_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = _patched_load
# Whisper Speech Recognition (Added in v2.1)
try:
    from whisper_engine import WhisperEngine
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("⚠️ Warning: whisper_engine.py not found. Whisper function disabled.")


CUDA_AVAILABLE = torch.cuda.is_available()
CUDA_DEVICE = torch.cuda.get_device_name(0) if CUDA_AVAILABLE else "CPU"
# ==========================================

# ==========================================
# EXE Support: Resource Path Helper
# ==========================================
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path



def setup_ffmpeg():
    ffmpeg_exe = resource_path("ffmpeg/ffmpeg.exe")
    ffprobe_exe = resource_path("ffmpeg/ffprobe.exe")
    
    if ffmpeg_exe.exists():
        AudioSegment.converter = str(ffmpeg_exe)
        AudioSegment.ffmpeg = str(ffmpeg_exe)
        AudioSegment.ffprobe = str(ffprobe_exe)
        print(f"Local FFmpeg loaded: {ffmpeg_exe}")
    else:
        print("Local FFmpeg not found. Using system default.")

class VoicevoxCoquiGUI:
    def __init__(self, root):
        setup_ffmpeg()
        
        self.root = root
        gpu_status = f"GPU: {CUDA_DEVICE}" if CUDA_AVAILABLE else "CPU Mode"
        self.root.title(f"🎙️ ROGOAI Voice Studio v2.4 EN - {gpu_status}")

        try:
            icon_path = resource_path("make_icon/icon.ico")
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except:
            pass
        
        self.root.geometry("850x920") 
        
        self.app_data = self.get_app_data_path()
        self.voicevox_server_url = "http://127.0.0.1:50021"
        
        self.coqui_enabled = False
        self.coqui_model = None
        self.samples_dir = self.app_data / "samples"
        self.samples_dir.mkdir(parents=True, exist_ok=True)
        
        self.generation_stop_flag = False
        self.config_file = self.app_data / "config.json"
        
        # Whisper Engine
        self.whisper_engine = None
        self.whisper_model_var = tk.StringVar(value='base')
        self.whisper_language_var = tk.StringVar(value='ja')
        self.whisper_format_var = tk.StringVar(value='text')
        
        # Recording (v2.3)
        self.audio_input_method_var = tk.StringVar(value='file')  # 'file' or 'mic'
        self.is_recording = False
        self.recording_data = []
        self.recording_start_time = None
        self.recording_stream = None
        self.recording_timer_id = None
        self.recordings_dir = self.app_data / 'recordings'
        self.recordings_dir.mkdir(exist_ok=True)
        self.recording_output_dir_var = tk.StringVar(value=str(self.recordings_dir))
        
        self.selected_audio_file = None
        self.load_config()
        
        # v2.2 New Features
        self.presets = self.config.get('presets', {})
        self.current_preset = tk.StringVar(value='Default')
        self.text_history = self.config.get('text_history', [])
        self.templates = self.config.get('templates', {})
        self.auto_backup_enabled = True
        self.backup_timer_id = None
        
        # v2.3 Message settings
        self.show_recording_complete_message = self.config.get('show_recording_complete_message', True)
        
        self.voicevox_speakers = []
        self.build_gui()
        self.initialize_app_async()
        
        # v2.2 Create Default Preset
        if 'Default' not in self.presets:
            self.presets['Default'] = {
                'engine': 'coqui',
                'speed': 1.0,
                'volume': 1.0,
                'pitch': 0.0,
                'intonation': 1.0,
                'pre_silence': 0.1,
                'post_silence': 0.1,
                'format': 'wav'
            }
            self.config['presets'] = self.presets
            self.save_config()
        
        # v2.2 Start Auto Backup
        self.start_auto_backup()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def get_app_data_path(self):
        if getattr(sys, 'frozen', False):
            base = Path(os.path.dirname(sys.executable))
        else:
            base = Path(os.path.dirname(os.path.abspath(__file__)))
        
        app_path = base / 'user_data'
        app_path.mkdir(parents=True, exist_ok=True)
        (app_path / 'outputs').mkdir(exist_ok=True)
        (app_path / 'logs').mkdir(exist_ok=True)
        return app_path

    def initialize_app_async(self):
        def _init():
            try:
                self.download_sample_voices()
                time.sleep(1.0)
                
                default_wav = self.samples_dir / "de_female_official.wav"
                if not default_wav.exists() or default_wav.stat().st_size == 0:
                    self._download_file("de_female_official.wav", "https://huggingface.co/coqui/XTTS-v2/resolve/main/samples/de_sample.wav")
                    time.sleep(1.0)

                self.root.after(0, self.refresh_coqui_speakers)
                self.initialize_coqui()
                
                self.check_voicevox_connection()
                self.root.after(0, self.refresh_voicevox_speakers)
                
            except Exception as e:
                print(f"Init Error: {e}")
                self.root.after(0, lambda: messagebox.showerror("Startup Error", f"Error during initialization:\n{e}"))

        threading.Thread(target=_init, daemon=True).start()

    def download_sample_voices(self):
        targets = [
            ("de_female_official.wav", "https://huggingface.co/coqui/XTTS-v2/resolve/main/samples/de_sample.wav"),
            ("en_female_official.wav", "https://huggingface.co/coqui/XTTS-v2/resolve/main/samples/en_sample.wav"),
            ("fr_male_official.wav", "https://huggingface.co/coqui/XTTS-v2/resolve/main/samples/fr_sample.wav"),
            ("it_female_official.wav", "https://huggingface.co/coqui/XTTS-v2/resolve/main/samples/it_sample.wav"),
            ("es_female_official.wav", "https://huggingface.co/coqui/XTTS-v2/resolve/main/samples/es_sample.wav"),
            ("pt_female_official.wav", "https://huggingface.co/coqui/XTTS-v2/resolve/main/samples/pt_sample.wav"),
            ("pl_female_official.wav", "https://huggingface.co/coqui/XTTS-v2/resolve/main/samples/pl_sample.wav"),
            ("zh_female_official.wav", "https://huggingface.co/coqui/XTTS-v2/resolve/main/samples/zh-cn_sample.wav"),
            ("nl_female_official.wav", "https://huggingface.co/coqui/XTTS-v2/resolve/main/samples/nl_sample.wav"),
            ("ar_female_official.wav", "https://huggingface.co/coqui/XTTS-v2/resolve/main/samples/ar_sample.wav"),
            ("ko_female_official.wav", "https://huggingface.co/coqui/XTTS-v2/resolve/main/samples/ko_sample.wav"),
        ]
        for fname, url in targets:
            self._download_file(fname, url)

    def _download_file(self, fname, url):
        save_path = self.samples_dir / fname
        if save_path.exists() and save_path.stat().st_size > 0: return
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            self.root.after(0, lambda m=f"📥 DL: {fname}...": self.status_bar.config(text=m))
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                with open(save_path, 'wb') as f: f.write(response.content)
        except: pass

    def initialize_coqui(self):
        if self.coqui_model: return
        try:
            self.root.after(0, lambda: self.coqui_status_label.config(text="Coqui TTS: Initializing...", foreground="orange"))
            self.root.after(0, lambda: self.status_bar.config(text="🚀 Loading AI Engine (Please wait)..."))
            
            from TTS.api import TTS
            self.coqui_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
            if CUDA_AVAILABLE: self.coqui_model.to("cuda")
            self.coqui_enabled = True
            
            self.root.after(0, lambda: self.coqui_status_label.config(text="Coqui TTS: Ready", foreground="green"))
            self.root.after(0, lambda: self.status_bar.config(text="✓ Coqui TTS Engine is Ready"))
            
        except Exception as e:
            self.root.after(0, lambda: self.coqui_status_label.config(text="Coqui TTS: Failed", foreground="red"))
            err_msg = str(e)
            print(f"Coqui Init Error: {err_msg}")
            self.root.after(0, lambda: messagebox.showerror("Engine Error", f"Failed to start Coqui TTS.\n\nError:\n{err_msg}"))

    def build_gui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 1: Speech Recognition (STT)
        if WHISPER_AVAILABLE:
            self.tab_stt = ttk.Frame(self.notebook)
            self.notebook.add(self.tab_stt, text="🎤 STT (Speech Recog)")
            self.build_stt_tab(self.tab_stt)
        
        # Tab 2: Voice Generation (TTS)
        self.tab_tts = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tts, text="🗣️ TTS (Voice Gen)")
        self.build_tts_tab(self.tab_tts)

    def build_tts_tab(self, parent):
        main_frame = ttk.Frame(parent, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Server Status
        status_frame = ttk.LabelFrame(main_frame, text="Server/Engine Status", padding="2")
        status_frame.pack(fill=tk.X, pady=2)
        
        self.coqui_status_label = ttk.Label(status_frame, text="Coqui TTS: Waiting...", foreground="orange")
        self.coqui_status_label.pack(side=tk.LEFT, padx=10)
        ttk.Label(status_frame, text="|").pack(side=tk.LEFT, padx=5)

        self.voicevox_status_label = ttk.Label(status_frame, text="VOICEVOX: Checking...")
        self.voicevox_status_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(status_frame, text="🔄 Reconnect", command=self.reconnect_voicevox_async, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Label(status_frame, text="* Start VOICEVOX app to reconnect", font=("", 8), foreground="gray").pack(side=tk.LEFT, padx=5)
        
        # 2. Engine Selection
        engine_frame = ttk.LabelFrame(main_frame, text="🎙️ Voice Engine Selection", padding="2")
        engine_frame.pack(fill=tk.X, pady=2)
        
        default_engine = self.config.get('engine', 'coqui') 
        self.engine_var = tk.StringVar(value=default_engine)
        
        ttk.Radiobutton(engine_frame, text="Coqui TTS XTTS (File Clone)", variable=self.engine_var, value="coqui", command=self.update_ui_state).pack(side=tk.LEFT, padx=15)
        ttk.Radiobutton(engine_frame, text="VOICEVOX (Preset Char)", variable=self.engine_var, value="voicevox", command=self.update_ui_state).pack(side=tk.LEFT, padx=15)
        
        # Preset UI
        self.build_preset_ui(main_frame)

        # 3. Character Settings
        self.char_frame = ttk.LabelFrame(main_frame, text="👤 Speaker Settings", padding="2")
        self.char_frame.pack(fill=tk.X, pady=2)

        # --- Coqui TTS UI ---
        self.coqui_container = ttk.Frame(self.char_frame)
        ttk.Label(self.coqui_container, text="Voice File:").grid(row=0, column=0, sticky=tk.W, padx=(5,2))
        
        self.coqui_speaker_var = tk.StringVar()
        self.coqui_speaker_combo = ttk.Combobox(self.coqui_container, textvariable=self.coqui_speaker_var, width=30, state="readonly")
        self.coqui_speaker_combo.grid(row=0, column=1, padx=2)
        
        ttk.Button(self.coqui_container, text="Folder", command=self.open_samples_dir, width=8).grid(row=0, column=2, padx=2)
        ttk.Button(self.coqui_container, text="Refresh", command=self.refresh_coqui_speakers, width=8).grid(row=0, column=3, padx=2)
        
        ttk.Label(self.coqui_container, text="Lang:").grid(row=0, column=4, sticky=tk.W, padx=(10, 2))
        self.language_var = tk.StringVar(value=self.config.get('language', 'ja'))
        self.language_combo = ttk.Combobox(self.coqui_container, textvariable=self.language_var, width=8, state="readonly")
        self.language_combo['values'] = ['ja - JP', 'en - EN', 'zh-cn - CN', 'ko - KR', 'fr - FR', 'de - DE']
        self.language_combo.current(0)
        self.language_combo.grid(row=0, column=5, padx=2)

        # --- VOICEVOX UI ---
        self.vv_container = ttk.Frame(self.char_frame)
        ttk.Label(self.vv_container, text="Character:").pack(side=tk.LEFT)
        self.vv_speaker_var = tk.StringVar()
        self.vv_speaker_combo = ttk.Combobox(self.vv_container, textvariable=self.vv_speaker_var, width=40, state="readonly")
        self.vv_speaker_combo.pack(side=tk.LEFT, padx=5)

        # 4. Parameters
        params_container = ttk.Frame(main_frame)
        params_container.pack(fill=tk.X, pady=2)
        
        param_frame = ttk.LabelFrame(params_container, text="🎚️ Voice Parameters ([VV]: VOICEVOX only)", padding="2")
        param_frame.pack(fill=tk.X)

        COLOR_COMMON = "#d4edda"
        COLOR_VV = "#cce5ff"
        lbl_speed = tk.Label(param_frame, text="Speed:", bg=COLOR_COMMON, padx=5)
        lbl_speed.grid(row=0, column=0, sticky=tk.W+tk.E, padx=2, pady=2)
        self.speed_var = tk.DoubleVar(value=self.config.get('speed', 1.0))
        tk.Scale(param_frame, from_=0.5, to=2.0, resolution=0.01, orient=tk.HORIZONTAL, variable=self.speed_var, showvalue=0, length=120, troughcolor=COLOR_COMMON, bg="#f0f0f0", bd=0).grid(row=0, column=1, padx=5)
        
        lbl_vol = tk.Label(param_frame, text="Volume:", bg=COLOR_COMMON, padx=5)
        lbl_vol.grid(row=0, column=2, sticky=tk.W+tk.E, padx=2, pady=2)
        self.volume_var = tk.DoubleVar(value=self.config.get('volume', 1.0))
        tk.Scale(param_frame, from_=0.0, to=2.0, resolution=0.01, orient=tk.HORIZONTAL, variable=self.volume_var, showvalue=0, length=120, troughcolor=COLOR_COMMON, bg="#f0f0f0", bd=0).grid(row=0, column=3, padx=5)

        lbl_pitch = tk.Label(param_frame, text="Pitch [VV]:", bg=COLOR_VV, padx=5)
        lbl_pitch.grid(row=1, column=0, sticky=tk.W+tk.E, padx=2, pady=2)
        self.pitch_var = tk.DoubleVar(value=self.config.get('pitch', 0.0))
        self.pitch_scale = tk.Scale(param_frame, from_=-0.15, to=0.15, resolution=0.01, orient=tk.HORIZONTAL, variable=self.pitch_var, showvalue=0, length=120, troughcolor=COLOR_VV, bg="#f0f0f0", bd=0)
        self.pitch_scale.grid(row=1, column=1, padx=5)

        lbl_int = tk.Label(param_frame, text="Intonation [VV]:", bg=COLOR_VV, padx=5)
        lbl_int.grid(row=1, column=2, sticky=tk.W+tk.E, padx=2, pady=2)
        self.intonation_var = tk.DoubleVar(value=self.config.get('intonation', 1.0))
        self.intonation_scale = tk.Scale(param_frame, from_=0.0, to=2.0, resolution=0.01, orient=tk.HORIZONTAL, variable=self.intonation_var, showvalue=0, length=120, troughcolor=COLOR_VV, bg="#f0f0f0", bd=0)
        self.intonation_scale.grid(row=1, column=3, padx=5)

        silence_frame = ttk.LabelFrame(params_container, text="🔇 Silence (sec)", padding="2")
        silence_frame.pack(fill=tk.X, pady=2)
        ttk.Label(silence_frame, text="Pre:").pack(side=tk.LEFT, padx=2)
        self.pre_silence_var = tk.DoubleVar(value=self.config.get('pre_silence', 0.1))
        ttk.Entry(silence_frame, textvariable=self.pre_silence_var, width=4).pack(side=tk.LEFT)
        ttk.Label(silence_frame, text="Post:").pack(side=tk.LEFT, padx=5)
        self.post_silence_var = tk.DoubleVar(value=self.config.get('post_silence', 0.1))
        ttk.Entry(silence_frame, textvariable=self.post_silence_var, width=4).pack(side=tk.LEFT)
        ttk.Label(silence_frame, text="Punctuation:").pack(side=tk.LEFT, padx=5)
        self.punctuation_silence_var = tk.DoubleVar(value=self.config.get('punctuation_silence', 0.3))
        ttk.Entry(silence_frame, textvariable=self.punctuation_silence_var, width=4).pack(side=tk.LEFT)
        
        # Preview Button
        ttk.Label(silence_frame, text="").pack(side=tk.LEFT, padx=10)
        ttk.Button(silence_frame, text="🔊 Preview (30 chars)", 
                  command=self.preview_voice, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(silence_frame, text="❓", 
                  command=self.show_preview_help, width=3).pack(side=tk.LEFT, padx=1)


        # 5. Text Input
        text_frame = ttk.LabelFrame(main_frame, text="📝 Text Input", padding="2")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        tool_frame = ttk.Frame(text_frame)
        tool_frame.pack(fill=tk.X)
        
        ttk.Button(tool_frame, text="📂 Load File", command=self.load_text_file, width=12).pack(side=tk.LEFT)
        tk.Button(tool_frame, text="🗑️ Clear", command=self.clear_text_input, bg="#dc3545", fg="white", font=("", 8, "bold"), relief=tk.RAISED, width=8).pack(side=tk.LEFT, padx=10)
        ttk.Button(tool_frame, text="📄 Open log.txt", command=self.open_output_dir, width=14).pack(side=tk.LEFT, padx=5)
        
        self.text_input = scrolledtext.ScrolledText(text_frame, width=60, height=5)
        self.text_input.pack(fill=tk.BOTH, expand=True)

        # 6. Output Settings
        output_frame = ttk.LabelFrame(main_frame, text="💾 Output Settings", padding="5")
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(output_frame, text="Folder:").grid(row=0, column=0, sticky=tk.W, padx=5)
        default_output = self.config.get('output_dir', str(self.app_data / 'outputs'))
        self.output_dir_var = tk.StringVar(value=default_output)
        ttk.Entry(output_frame, textvariable=self.output_dir_var, width=28).grid(row=0, column=1, padx=5, columnspan=2, sticky=tk.W+tk.E)
        
        ttk.Button(output_frame, text="...", command=self.browse_output_dir, width=5).grid(row=0, column=3, padx=2)
        ttk.Button(output_frame, text="Open", command=self.open_output_dir, width=5).grid(row=0, column=4, padx=2)
        
        ttk.Label(output_frame, text="Format:").grid(row=0, column=5, sticky=tk.W, padx=10)
        self.format_var = tk.StringVar(value=self.config.get('format', 'wav'))
        ttk.Combobox(output_frame, textvariable=self.format_var, values=['wav', 'mp3'], width=5, state="readonly").grid(row=0, column=6, sticky=tk.W, padx=2)

        ttk.Label(output_frame, text="Prefix:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.prefix_var = tk.StringVar(value=self.config.get('prefix', 'voice'))
        ttk.Entry(output_frame, textvariable=self.prefix_var, width=15).grid(row=1, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(output_frame, text="Seq Digits:").grid(row=1, column=2, sticky=tk.E, padx=2)
        self.seq_digits_var = tk.IntVar(value=self.config.get('seq_digits', 3))
        ttk.Spinbox(output_frame, from_=1, to=10, textvariable=self.seq_digits_var, width=3).grid(row=1, column=3, sticky=tk.W, padx=2)

        ttk.Label(output_frame, text="Naming:").grid(row=2, column=0, sticky=tk.W, padx=5)
        # ★ FIXED: Changed default from {ID}_{接頭辞}_{連番} to {ID}_{Prefix}_{Seq}
        self.filename_pattern_var = tk.StringVar(value=self.config.get('filename_pattern', '{ID}_{Prefix}_{Seq}'))
        self.pattern_entry = ttk.Entry(output_frame, textvariable=self.filename_pattern_var)
        self.pattern_entry.grid(row=2, column=1, columnspan=5, sticky=tk.W+tk.E, padx=5)
        
        tag_frame = ttk.Frame(output_frame)
        tag_frame.grid(row=3, column=1, columnspan=5, sticky=tk.W, pady=2)
        
        def add_tag(tag):
            self.pattern_entry.insert(tk.INSERT, tag)
        
        # ★ FIXED: English Tags
        ttk.Label(tag_frame, text="Insert Tag:", font=("", 8), foreground="gray").pack(side=tk.LEFT, padx=(5,5))
        ttk.Button(tag_frame, text="+Text(7)", command=lambda: add_tag("{Text}"), width=8).pack(side=tk.LEFT, padx=1)
        ttk.Button(tag_frame, text="+ID", command=lambda: add_tag("{ID}"), width=5).pack(side=tk.LEFT, padx=1)
        ttk.Button(tag_frame, text="+Time", command=lambda: add_tag("{Date}"), width=6).pack(side=tk.LEFT, padx=1)
        ttk.Button(tag_frame, text="+Prefix", command=lambda: add_tag("{Prefix}"), width=9).pack(side=tk.LEFT, padx=1)
        ttk.Button(tag_frame, text="+Seq", command=lambda: add_tag("{Seq}"), width=6).pack(side=tk.LEFT, padx=1)

        
        
        # v2.2 Extended Features
        advanced_frame = ttk.Frame(main_frame)
        advanced_frame.pack(fill=tk.X, pady=3)
        
        ttk.Button(advanced_frame, text="📂 Batch Load Folder", command=self.batch_generate, width=20).pack(side=tk.LEFT, padx=3)
        ttk.Button(advanced_frame, text="📝 Templates", command=self.load_template, width=15).pack(side=tk.LEFT, padx=3)
        ttk.Button(advanced_frame, text="💾", command=self.save_template, width=3).pack(side=tk.LEFT, padx=1)
        ttk.Button(advanced_frame, text="❓", command=self.show_template_help, width=3).pack(side=tk.LEFT, padx=1)
        ttk.Button(advanced_frame, text="📋 History", command=self.show_text_history, width=10).pack(side=tk.LEFT, padx=3)


        # 7. Action Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        self.generate_button = tk.Button(button_frame, text="🎵 Start Generation", command=self.generate_voice, bg="#28a745", fg="white", font=("", 12, "bold"), padx=15, pady=5, relief=tk.RAISED, cursor="hand2")
        self.generate_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = tk.Button(button_frame, text="⏹️ Stop", command=self.stop_generation, bg="#dc3545", fg="white", font=("", 12, "bold"), padx=15, pady=5, relief=tk.RAISED, cursor="hand2", state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔔 Restore Popups", command=self.restore_popups).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔄 Reset Settings", command=self.reset_settings).pack(side=tk.LEFT, padx=5)

        self.status_bar = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.update_ui_state()

    def open_samples_dir(self):
        if not self.samples_dir.exists(): self.samples_dir.mkdir()
        if platform.system() == "Windows": os.startfile(self.samples_dir)
        elif platform.system() == "Darwin": subprocess.Popen(["open", self.samples_dir])
        else: subprocess.Popen(["xdg-open", self.samples_dir])

    def open_output_dir(self):
        path = Path(self.output_dir_var.get())
        if not path.exists(): path.mkdir(parents=True, exist_ok=True)
        if platform.system() == "Windows": os.startfile(path)
        elif platform.system() == "Darwin": subprocess.Popen(["open", path])
        else: subprocess.Popen(["xdg-open", path])

    def reconnect_voicevox_async(self):
        self.voicevox_status_label.config(text="VOICEVOX: Connecting...", foreground="orange")
        threading.Thread(target=self._reconnect_voicevox, daemon=True).start()

    def _reconnect_voicevox(self):
        try:
            requests.get(f"{self.voicevox_server_url}/version", timeout=2)
            self.root.after(0, lambda: self.voicevox_status_label.config(text="VOICEVOX: Connected", foreground="green"))
            self.root.after(0, self.refresh_voicevox_speakers)
            self.root.after(0, lambda: messagebox.showinfo("Success", "Connected to VOICEVOX!"))
        except:
            self.root.after(0, lambda: self.voicevox_status_label.config(text="VOICEVOX: Disconnected", foreground="red"))

    def update_ui_state(self):
        engine = self.engine_var.get()
        if engine == 'voicevox':
            self.vv_container.pack(fill=tk.X, expand=True)
            self.coqui_container.pack_forget()
            self.pitch_scale.config(state='normal', fg='black')
            self.intonation_scale.config(state='normal', fg='black')
        else:
            self.vv_container.pack_forget()
            self.coqui_container.pack(fill=tk.X, expand=True)
            self.pitch_scale.config(state='disabled', fg='gray')
            self.intonation_scale.config(state='disabled', fg='gray')
            if not self.coqui_speaker_combo['values']:
                self.refresh_coqui_speakers()

    def refresh_voicevox_speakers(self):
        self.voicevox_speakers = self.get_voicevox_speakers()
        speaker_values = [f"{s['name']} (ID: {s['id']})" for s in self.voicevox_speakers]
        self.vv_speaker_combo['values'] = speaker_values
        if self.voicevox_speakers:
            self.vv_speaker_combo.current(0)

    def refresh_coqui_speakers(self):
        options = []
        if self.samples_dir.exists():
            files = list(self.samples_dir.glob("*.wav")) + list(self.samples_dir.glob("*.mp3"))
            options = [f.name for f in files]
        if not options: options = ["(Sample folder is empty)"]
        self.coqui_speaker_combo['values'] = options
        
        default_target = "de_female_official.wav"
        if default_target in options: self.coqui_speaker_combo.current(options.index(default_target))
        else: self.coqui_speaker_combo.current(0)

    def get_first_7_chars(self, text):
        invalid_chars = [':', '*', '?', '"', '<', '>', '|', '/', '\\']
        clean_text = text.replace('\n', '').replace('\r', '').replace(' ', '').replace('　', '')
        for char in invalid_chars:
            clean_text = clean_text.replace(char, '')
        return clean_text[:7] if len(clean_text) >= 7 else clean_text.ljust(7, '_')

    def load_text_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text File", "*.txt"), ("All Files", "*.*")])
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.text_input.delete(1.0, tk.END)
                self.text_input.insert(1.0, f.read())

    def reset_settings(self):
        self.speed_var.set(1.0)
        self.pitch_var.set(0.0)
        self.intonation_var.set(1.0)
        self.volume_var.set(1.0)
        self.pre_silence_var.set(0.1)
        self.post_silence_var.set(0.1)
        self.punctuation_silence_var.set(0.3)
        self.status_bar.config(text="Settings reset.")
    
    def restore_popups(self):
        """Restore all popup notifications"""
        disabled_popups = []
        
        if not self.show_recording_complete_message:
            disabled_popups.append("Recording Complete")
        
        if not self.config.get('show_generation_complete', True):
            disabled_popups.append("Generation Complete")
        
        if not self.config.get('show_transcription_complete', True):
            disabled_popups.append("Transcription Complete")
        
        if not disabled_popups:
            messagebox.showinfo(
                "Popups",
                "All popups are already enabled."
            )
            return
        
        popup_list = "\n- ".join(disabled_popups)
        result = messagebox.askyesno(
            "Restore Popups",
            f"Restore the following popups?\n\n"
            f"- {popup_list}\n\n"
        )
        
        if result:
            self.show_recording_complete_message = True
            self.config['show_recording_complete_message'] = True
            self.config['show_generation_complete'] = True
            self.config['show_transcription_complete'] = True
            self.save_config()
            
            messagebox.showinfo("Done", "Popups restored.")
            self.status_bar.config(text="✅ Popups restored")
        else:
            self.status_bar.config(text="Cancelled.")

    def clear_text_input(self):
        if messagebox.askyesno("Confirm", "Clear text?"):
            self.text_input.delete(1.0, tk.END)

    def stop_generation(self):
        self.generation_stop_flag = True
        self.status_bar.config(text="⏹️ Stopping...")

    def generate_voice(self):
        text = self.text_input.get(1.0, tk.END).strip()
        if not text: return
        if self.engine_var.get() == 'coqui' and not self.coqui_enabled:
            messagebox.showwarning("Busy", "Coqui TTS is still loading.")
            return
        
        segments = [s.strip() for s in text.split('\n\n') if s.strip()]
        self.generation_stop_flag = False
        self.generate_button.config(state='disabled', text="🎵 Generating...")
        self.stop_button.config(state='normal')
        threading.Thread(target=self._generate_voice_async, args=(segments,), daemon=True).start()

    def generate_filename(self, speaker_id, index, extension, text="", engine="VOICEVOX"):
        # ★ FIXED: Default pattern to English
        pattern = self.filename_pattern_var.get()
        if not pattern: pattern = "{ID}_{Prefix}_{Seq}"
        
        prefix = self.prefix_var.get()
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        first_7 = self.get_first_7_chars(text)
        
        digits = self.seq_digits_var.get()
        seq_str = str(index).zfill(digits)
        
        if engine == "CoquiTTS": chara_id = "CQ"
        else: chara_id = f"{speaker_id:03d}"
        
        # ★ FIXED: Logic to replace English tags
        fname = pattern.replace("{Text}", first_7)
        fname = fname.replace("{ID}", f"ID{chara_id}")
        fname = fname.replace("{Date}", timestamp)
        fname = fname.replace("{Prefix}", prefix)
        fname = fname.replace("{Seq}", seq_str)
        
        return f"{fname}.{extension}"

    def _generate_voice_async(self, segments):
        try:
            output_dir = Path(self.output_dir_var.get())
            output_dir.mkdir(parents=True, exist_ok=True)
            speed = self.speed_var.get()
            volume = self.volume_var.get()
            pre_sil = self.pre_silence_var.get()
            post_sil = self.post_silence_var.get()
            ext = self.format_var.get()
            
            self.root.after(0, lambda: self._show_progress_dialog(len(segments)))
            
            count = 0
            for i, seg in enumerate(segments, 1):
                if self.generation_stop_flag: break
                
                self.root.after(0, lambda p=int((i-1)/len(segments)*100), c=i: self._update_progress(p, f"Generating: {c}/{len(segments)}"))
                
                if self.engine_var.get() == 'coqui':
                    wav = self.run_coqui(seg, speed)
                    engine_name = "CoquiTTS"
                else:
                    wav = self.run_voicevox(seg)
                    engine_name = "VOICEVOX"
                
                audio = self.post_process_audio(wav, volume, pre_sil, post_sil)
                fname = self.generate_filename(self.get_speaker_id(), i, ext, seg, engine_name)
                
                if ext == "mp3": audio.export(output_dir / fname, format="mp3", bitrate="192k")
                else: audio.export(output_dir / fname, format="wav")
                self.write_daily_log(fname, seg, output_dir)
                count += 1
            
            self.root.after(0, lambda: self._update_progress(100, "Done!"))
            self.root.after(0, lambda: self._on_generation_complete(count, len(segments), output_dir))
        except Exception as e:
            traceback.print_exc()
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("Error", msg))
        finally:
            self.root.after(0, lambda: self.generate_button.config(state='normal', text="🎵 Start Generation"))
            self.root.after(0, lambda: self.stop_button.config(state='disabled'))
            self.root.after(0, self._close_progress_dialog)
            self.root.after(0, self.save_config)

    def _show_progress_dialog(self, total):
        self.progress_dialog = tk.Toplevel(self.root)
        self.progress_dialog.title("Generating")
        self.progress_dialog.geometry("400x120")
        ttk.Label(self.progress_dialog, text="Generating audio...", font=("", 11)).pack(pady=10)
        self.progress_var = tk.DoubleVar()
        ttk.Progressbar(self.progress_dialog, variable=self.progress_var, maximum=100, length=350).pack()
        self.progress_status_var = tk.StringVar()
        ttk.Label(self.progress_dialog, textvariable=self.progress_status_var).pack(pady=5)

    def _update_progress(self, percent, status):
        if hasattr(self, 'progress_var'): self.progress_var.set(percent)
        if hasattr(self, 'progress_status_var'): self.progress_status_var.set(status)
    
    def _close_progress_dialog(self):
        if hasattr(self, 'progress_dialog'): self.progress_dialog.destroy()

    def _on_generation_complete(self, count, total, output_dir):
        if not self.config.get('show_generation_complete', True):
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Complete")
        dialog.geometry("450x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="✅ Generation Complete", 
                 font=("", 12, "bold")).pack(pady=10)
        
        msg_frame = ttk.Frame(dialog)
        msg_frame.pack(pady=10)
        
        ttk.Label(msg_frame, text=f"Files: {count}/{total}").pack()
        ttk.Label(msg_frame, text=f"Saved to: {output_dir}").pack()
        ttk.Label(msg_frame, text="* Audio files and log (YYYYMMDD_log.txt) saved", 
                 font=("", 8), foreground="gray").pack()
        
        dont_show_var = tk.BooleanVar()
        check_frame = ttk.Frame(dialog)
        check_frame.pack(pady=15)
        
        ttk.Checkbutton(check_frame, text="Don't show this again", 
                       variable=dont_show_var).pack()
        
        info_label = ttk.Label(dialog, 
                              text="* Use 'Restore Popups' to enable again",
                              font=("", 8), foreground="blue")
        info_label.pack(pady=5)
        
        def on_ok():
            if dont_show_var.get():
                self.config['show_generation_complete'] = False
                self.save_config()
            dialog.destroy()
        
        ttk.Button(dialog, text="OK", command=on_ok, width=15).pack(pady=10)
        
        dialog.protocol("WM_DELETE_WINDOW", on_ok)

    def run_coqui(self, text, speed):
        if not self.coqui_model: raise Exception("Engine initializing...")
        fname = self.coqui_speaker_var.get()
        lang = self.language_var.get().split(' - ')[0]
        temp = self.app_data / "temp.wav"
        self.coqui_model.tts_to_file(text=text, speaker_wav=str(self.samples_dir / fname), language=lang, file_path=str(temp), speed=speed)
        with open(temp, 'rb') as f: data = f.read()
        return data

    def run_voicevox(self, text):
        sid = self.get_speaker_id()
        q = requests.post(f"{self.voicevox_server_url}/audio_query?text={urllib.parse.quote(text)}&speaker={sid}").json()
        q['speedScale'] = self.speed_var.get()
        q['volumeScale'] = self.volume_var.get()
        q['pitchScale'] = self.pitch_var.get()
        q['intonationScale'] = self.intonation_var.get()
        return requests.post(f"{self.voicevox_server_url}/synthesis?speaker={sid}", json=q).content

    def post_process_audio(self, wav_bytes, volume, pre, post):
        audio = AudioSegment.from_wav(io.BytesIO(wav_bytes))
        if volume != 1.0 and volume > 0:
            import math
            audio = audio + (20 * math.log10(volume))
        if pre > 0: audio = AudioSegment.silent(duration=int(pre*1000)) + audio
        if post > 0: audio = audio + AudioSegment.silent(duration=int(post*1000))
        return audio

    def check_voicevox_connection(self):
        try: requests.get(f"{self.voicevox_server_url}/version", timeout=1)
        except: self.voicevox_status_label.config(text="VOICEVOX: Disconnected", foreground="red")

    def get_voicevox_speakers(self):
        try:
            res = requests.get(f"{self.voicevox_server_url}/speakers")
            return [{'name': f"{s['name']}-{st['name']}", 'id': st['id']} for s in res.json() for st in s['styles']]
        except: return []

    def get_speaker_id(self):
        val = self.vv_speaker_var.get()
        for s in self.voicevox_speakers:
            if f"{s['name']} (ID: {s['id']})" == val: return s['id']
        return 1

    def browse_output_dir(self):
        d = self.browse_folder_with_file_preview(
            title="Select Output Folder",
            initialdir=self.output_dir_var.get()
        )
        if d: self.output_dir_var.set(d)
    
    def browse_folder_with_file_preview(self, title="Select Folder", initialdir=None):
        """
        TreeView-based Explorer-like folder selector
        """
        class FolderBrowserDialog:
            def __init__(self, parent, title, initialdir):
                self.result = None
                self.dialog = tk.Toplevel(parent)
                self.dialog.title(title)
                self.dialog.geometry("700x500")
                self.dialog.transient(parent)
                self.dialog.grab_set()
                
                if initialdir and Path(initialdir).exists():
                    self.current_path = Path(initialdir)
                else:
                    self.current_path = Path.home()
                
                self._build_ui()
                self._populate_tree()
                
                self.dialog.update_idletasks()
                x = (parent.winfo_screenwidth() // 2) - (700 // 2)
                y = (parent.winfo_screenheight() // 2) - (500 // 2)
                self.dialog.geometry(f"+{x}+{y}")
            
            def _build_ui(self):
                path_frame = ttk.Frame(self.dialog)
                path_frame.pack(fill=tk.X, padx=10, pady=5)
                
                ttk.Label(path_frame, text="Current:").pack(side=tk.LEFT)
                self.path_var = tk.StringVar(value=str(self.current_path))
                ttk.Entry(path_frame, textvariable=self.path_var, 
                         state='readonly').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
                
                ttk.Button(path_frame, text="↑", width=3,
                          command=self._go_parent).pack(side=tk.LEFT, padx=2)
                ttk.Button(path_frame, text="Desktop", width=10,
                          command=self._go_desktop).pack(side=tk.LEFT, padx=2)
                ttk.Button(path_frame, text="📁 New", width=6,
                          command=self._create_folder).pack(side=tk.LEFT, padx=2)
                
                tree_frame = ttk.Frame(self.dialog)
                tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
                
                scrollbar = ttk.Scrollbar(tree_frame)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                self.tree = ttk.Treeview(tree_frame, yscrollcommand=scrollbar.set,
                                        selectmode='browse')
                self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.config(command=self.tree.yview)
                
                self.tree['columns'] = ('type', 'size')
                self.tree.column('#0', width=400, minwidth=200)
                self.tree.column('type', width=100, minwidth=80)
                self.tree.column('size', width=100, minwidth=80)
                
                self.tree.heading('#0', text='Name')
                self.tree.heading('type', text='Type')
                self.tree.heading('size', text='Size')
                
                self.tree.bind('<Double-Button-1>', self._on_double_click)
                self.tree.bind('<<TreeviewSelect>>', self._on_select)
                
                button_frame = ttk.Frame(self.dialog)
                button_frame.pack(fill=tk.X, padx=10, pady=10)
                
                ttk.Button(button_frame, text="OK", width=10,
                          command=self._on_ok).pack(side=tk.RIGHT, padx=5)
                ttk.Button(button_frame, text="Cancel", width=10,
                          command=self._on_cancel).pack(side=tk.RIGHT, padx=5)
                
                ttk.Label(button_frame, 
                         text="💡 Double click to open folder, select and click OK to choose.",
                         foreground="blue", font=("", 9)).pack(side=tk.LEFT)
            
            def _populate_tree(self):
                for item in self.tree.get_children():
                    self.tree.delete(item)
                
                try:
                    items = list(self.current_path.iterdir())
                    
                    folders = sorted([x for x in items if x.is_dir()], 
                                   key=lambda x: x.name.lower())
                    files = sorted([x for x in items if x.is_file()], 
                                 key=lambda x: x.name.lower())
                    
                    for folder in folders:
                        try:
                            self.tree.insert('', 'end', 
                                           text=f"📁 {folder.name}",
                                           values=('Folder', ''),
                                           tags=('folder',))
                        except:
                            pass
                    
                    for file in files:
                        try:
                            size = file.stat().st_size
                            size_str = self._format_size(size)
                            self.tree.insert('', 'end',
                                           text=f"📄 {file.name}",
                                           values=('File', size_str),
                                           tags=('file',))
                        except:
                            pass
                    
                    self.tree.tag_configure('file', foreground='gray')
                    
                except PermissionError:
                    self.tree.insert('', 'end', text='⚠️ Permission Denied')
                except Exception as e:
                    self.tree.insert('', 'end', text=f'⚠️ Error: {str(e)}')
            
            def _format_size(self, size):
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024.0:
                        return f"{size:.1f} {unit}"
                    size /= 1024.0
                return f"{size:.1f} TB"
            
            def _on_double_click(self, event):
                selection = self.tree.selection()
                if not selection:
                    return
                
                item = selection[0]
                tags = self.tree.item(item, 'tags')
                
                if 'folder' in tags:
                    item_text = self.tree.item(item, 'text')
                    folder_name = item_text.replace('📁 ', '')
                    new_path = self.current_path / folder_name
                    
                    if new_path.exists() and new_path.is_dir():
                        self.current_path = new_path
                        self.path_var.set(str(self.current_path))
                        self._populate_tree()
            
            def _on_select(self, event):
                selection = self.tree.selection()
                if not selection:
                    return
                
                item = selection[0]
                tags = self.tree.item(item, 'tags')
                
                if 'folder' in tags:
                    item_text = self.tree.item(item, 'text')
                    folder_name = item_text.replace('📁 ', '')
                    selected_path = self.current_path / folder_name
                    self.path_var.set(str(selected_path))
                else:
                    self.path_var.set(str(self.current_path))
            
            def _go_parent(self):
                if self.current_path.parent != self.current_path:
                    self.current_path = self.current_path.parent
                    self.path_var.set(str(self.current_path))
                    self._populate_tree()
            
            def _go_desktop(self):
                self.current_path = Path.home() / "Desktop"
                if not self.current_path.exists():
                    self.current_path = Path.home()
                self.path_var.set(str(self.current_path))
                self._populate_tree()
            
            def _create_folder(self):
                from tkinter import simpledialog, messagebox
                
                folder_name = simpledialog.askstring(
                    "New Folder",
                    "Enter folder name:",
                    parent=self.dialog
                )
                
                if folder_name:
                    invalid_chars = '<>:"/\\|?*'
                    if any(c in folder_name for c in invalid_chars):
                        messagebox.showerror(
                            "Error",
                            f"Invalid characters:\n{invalid_chars}"
                        )
                        return
                    
                    new_folder = self.current_path / folder_name
                    
                    if new_folder.exists():
                        messagebox.showwarning("Warning", "Folder already exists")
                        return
                    
                    try:
                        new_folder.mkdir(parents=True, exist_ok=True)
                        self._populate_tree()
                        messagebox.showinfo("Success", f"Created: {folder_name}")
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to create folder:\n{str(e)}")
            
            def _on_ok(self):
                selected_path = Path(self.path_var.get())
                
                if selected_path.exists() and selected_path.is_dir():
                    self.result = str(selected_path)
                    self.dialog.destroy()
                else:
                    from tkinter import messagebox
                    messagebox.showwarning("Warning", "Please select a valid folder.")
            
            def _on_cancel(self):
                self.result = None
                self.dialog.destroy()
        
        browser = FolderBrowserDialog(self.root, title, initialdir)
        self.root.wait_window(browser.dialog)
        return browser.result

    def load_config(self):
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f: self.config = json.load(f)
        else: self.config = {}

    def save_config(self):
        try:
            self.config.update({
                'engine': self.engine_var.get(),
                'speaker_id': self.get_speaker_id(),
                'speed': self.speed_var.get(),
                'pitch': self.pitch_var.get(),
                'intonation': self.intonation_var.get(),
                'volume': self.volume_var.get(),
                'pre_silence': self.pre_silence_var.get(),
                'post_silence': self.post_silence_var.get(),
                'punctuation_silence': self.punctuation_silence_var.get(),
                'output_dir': self.output_dir_var.get(),
                'format': self.format_var.get(),
                'filename_pattern': self.filename_pattern_var.get(),
                'seq_digits': self.seq_digits_var.get(),
                'prefix': self.prefix_var.get(),
                'language': self.language_var.get(),
                'show_recording_complete_message': self.show_recording_complete_message
            })
            with open(self.config_file, 'w', encoding='utf-8') as f: json.dump(self.config, f, indent=2)
        except: pass

    def write_daily_log(self, filename, text, output_dir):
        try:
            today = datetime.now().strftime("%Y%m%d")
            log_file = output_dir / f"{today}_log.txt"
            clean_text = ' '.join(text.split())
            with open(log_file, 'a', encoding='utf-8-sig') as f:
                f.write(f"{filename} : {clean_text}\n")
        except Exception as e:
            print(f"[Daily Logger] Log failed: {e}")

    def on_closing(self):
        self.save_config()
        self.root.destroy()


    
    # ==========================================
    # Whisper STT Functionality (v2.1+)
    # ==========================================
    
    def build_stt_tab(self, parent):
        """STT Tab UI Construction"""
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(title_frame, text="🎤 Whisper Speech Recognition", 
                 font=("", 12, "bold")).pack(side=tk.LEFT)
        ttk.Label(title_frame, text="Convert audio files to text", 
                 font=("", 9), foreground="gray").pack(side=tk.LEFT, padx=10)
        
        # Audio Input Method (v2.3)
        input_method_frame = ttk.LabelFrame(main_frame, text="🎙️ Audio Input Method", padding=10)
        input_method_frame.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(input_method_frame, text="Select from File", 
                       variable=self.audio_input_method_var, 
                       value='file',
                       command=self.toggle_audio_input_method).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(input_method_frame, text="Record from Mic", 
                       variable=self.audio_input_method_var, 
                       value='mic',
                       command=self.toggle_audio_input_method).pack(side=tk.LEFT, padx=10)
        
        # File Select UI
        self.file_select_frame = ttk.Frame(input_method_frame)
        self.file_select_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.file_select_frame, 
                 text="💡 Click 'Start Transcription' to select files (Multi-select allowed)", 
                 foreground="blue", font=("", 9)).pack(side=tk.LEFT, padx=5)
        
        # Recording UI
        self.recording_frame = ttk.Frame(input_method_frame)
        # Hidden by default
        
        # Recording Output
        rec_output_frame = ttk.Frame(self.recording_frame)
        rec_output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(rec_output_frame, text="Save to:", width=10).pack(side=tk.LEFT)
        ttk.Entry(rec_output_frame, textvariable=self.recording_output_dir_var, 
                 width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(rec_output_frame, text="...", 
                  command=self.browse_recording_output_dir, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(rec_output_frame, text="📂 Open", 
                  command=self.open_recording_output_dir, width=8).pack(side=tk.LEFT, padx=2)
        
        rec_buttons_frame = ttk.Frame(self.recording_frame)
        rec_buttons_frame.pack(fill=tk.X, pady=2)
        
        self.record_start_button = tk.Button(rec_buttons_frame, text="🔴 Start Recording", 
                                            command=self.start_recording,
                                            bg="#dc3545", fg="white", 
                                            font=("", 10, "bold"), width=15)
        self.record_start_button.pack(side=tk.LEFT, padx=5)
        
        self.record_stop_button = tk.Button(rec_buttons_frame, text="⏹️ Stop",
                                           command=self.stop_recording,
                                           state='disabled', width=10)
        self.record_stop_button.pack(side=tk.LEFT, padx=5)
        
        self.recording_time_var = tk.StringVar(value="Time: 00:00:00")
        ttk.Label(rec_buttons_frame, textvariable=self.recording_time_var,
                 font=("", 10)).pack(side=tk.LEFT, padx=10)
        
        self.recording_filename_var = tk.StringVar(value="")
        ttk.Label(self.recording_frame, textvariable=self.recording_filename_var,
                 foreground="gray", font=("", 8)).pack(fill=tk.X, pady=2)
        
        ttk.Label(self.recording_frame, 
                 text="💡 After recording, click 'Start Transcription' to select from recording folder.", 
                 foreground="blue", font=("", 9)).pack(fill=tk.X, pady=5)
        
        # Recognition Settings
        settings_frame = ttk.LabelFrame(main_frame, text="⚙️ Recognition Settings", padding=10)
        settings_frame.pack(fill=tk.X, pady=5)
        
        # Model
        model_frame = ttk.Frame(settings_frame)
        model_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(model_frame, text="Model:", width=10).pack(side=tk.LEFT)
        
        models = [
            ('base (Acc:85%)', 'base'),
            ('medium (Acc:95%)', 'medium'),
            ('large-v3 (Acc:98%)', 'large-v3')
        ]
        
        for text, value in models:
            ttk.Radiobutton(model_frame, text=text, 
                           variable=self.whisper_model_var, 
                           value=value).pack(side=tk.LEFT, padx=10)
        
        # Language
        lang_frame = ttk.Frame(settings_frame)
        lang_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(lang_frame, text="Lang:", width=10).pack(side=tk.LEFT)
        lang_combo = ttk.Combobox(lang_frame, textvariable=self.whisper_language_var,
                                  values=['ja - Japanese', 'en - English', 'zh - Chinese', 
                                         'ko - Korean', 'fr - French', 'de - German',
                                         'es - Spanish', 'it - Italian', 'pt - Portuguese'],
                                  state='readonly', width=20)
        lang_combo.pack(side=tk.LEFT, padx=5)
        
        # Format
        format_frame = ttk.Frame(settings_frame)
        format_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(format_frame, text="Format:", width=10).pack(side=tk.LEFT)
        ttk.Radiobutton(format_frame, text="Text", 
                       variable=self.whisper_format_var, 
                       value='text').pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="SRT Subtitle", 
                       variable=self.whisper_format_var, 
                       value='srt').pack(side=tk.LEFT, padx=5)
        
        # Action Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.transcribe_button = tk.Button(button_frame, text="🎤 Start Transcription", 
                                          command=self.start_transcription,
                                          bg="#28a745", fg="white", 
                                          font=("", 11, "bold"), height=2)
        self.transcribe_button.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.transcribe_stop_button = tk.Button(button_frame, text="⏹️ Stop",
                                               command=self.stop_transcription,
                                               state='disabled', width=10)
        self.transcribe_stop_button.pack(side=tk.LEFT, padx=5)
        
        # Auto Save Path
        auto_save_frame = ttk.Frame(main_frame)
        auto_save_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(auto_save_frame, text="Save Result to:", width=15).pack(side=tk.LEFT)
        default_stt_output = str(self.app_data / 'outputs')
        self.stt_output_dir_var = tk.StringVar(value=default_stt_output)
        ttk.Entry(auto_save_frame, textvariable=self.stt_output_dir_var, 
                 width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(auto_save_frame, text="...", 
                  command=self.browse_stt_output_dir, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(auto_save_frame, text="📂 Open", 
                  command=self.open_stt_output_dir, width=8).pack(side=tk.LEFT, padx=2)
        
        # Result Area
        result_frame = ttk.LabelFrame(main_frame, text="📝 Result", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.transcription_result = scrolledtext.ScrolledText(result_frame, 
                                                              width=60, height=15,
                                                              font=("", 10))
        self.transcription_result.pack(fill=tk.BOTH, expand=True)
        
        # Result Actions
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(action_frame, text="→ Transfer to TTS Tab", 
                  command=self.transfer_to_generation, width=25).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="🗑️ Clear", 
                  command=lambda: self.transcription_result.delete('1.0', tk.END), 
                  width=10).pack(side=tk.LEFT, padx=5)
    
    # ==========================================
    # v2.3 Recording Logic
    # ==========================================
    
    def toggle_audio_input_method(self):
        method = self.audio_input_method_var.get()
        
        if method == 'file':
            self.file_select_frame.pack(fill=tk.X, pady=5)
            self.recording_frame.pack_forget()
        else:  # mic
            self.file_select_frame.pack_forget()
            self.recording_frame.pack(fill=tk.X, pady=5)
            
            if not RECORDING_AVAILABLE:
                messagebox.showerror(
                    "Error",
                    "Recording not available.\n\n"
                    "Please install sounddevice and soundfile:\n"
                    "pip install sounddevice soundfile"
                )
                self.audio_input_method_var.set('file')
                self.toggle_audio_input_method()
    
    def start_recording(self):
        if not RECORDING_AVAILABLE:
            messagebox.showerror("Error", "Recording functionality is unavailable.")
            return
        
        try:
            output_dir = Path(self.recording_output_dir_var.get())
            if not output_dir.exists():
                output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"record_{timestamp}.wav"
            self.current_recording_file = output_dir / filename
            
            self.is_recording = True
            self.recording_data = []
            self.recording_start_time = time.time()
            
            self.record_start_button.config(state='disabled')
            self.record_stop_button.config(state='normal')
            self.recording_filename_var.set(f"Saving to: {filename}")
            
            # 16kHz Mono for Whisper
            self.recording_stream = sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype='float32',
                callback=self.recording_callback
            )
            self.recording_stream.start()
            
            self.update_recording_time()
            self.status_bar.config(text="🔴 Recording...")
            
        except Exception as e:
            messagebox.showerror("Recording Error", f"Failed to start recording:\n{str(e)}")
            self.is_recording = False
            self.record_start_button.config(state='normal')
            self.record_stop_button.config(state='disabled')
    
    def stop_recording(self):
        if not self.is_recording:
            return
        
        try:
            if self.recording_stream:
                self.recording_stream.stop()
                self.recording_stream.close()
                self.recording_stream = None
            
            if self.recording_timer_id:
                self.root.after_cancel(self.recording_timer_id)
                self.recording_timer_id = None
            
            if self.recording_data:
                audio_data = np.concatenate(self.recording_data, axis=0)
                sf.write(self.current_recording_file, audio_data, 16000)
                
                duration = time.time() - self.recording_start_time
                self.status_bar.config(text=f"✅ Recording finished: {duration:.1f}s")
                
                if self.show_recording_complete_message:
                    self.show_recording_complete_dialog(self.current_recording_file.name)
            else:
                self.status_bar.config(text="⚠ No recording data")
            
            self.is_recording = False
            self.recording_data = []
            self.record_start_button.config(state='normal')
            self.record_stop_button.config(state='disabled')
            self.recording_time_var.set("Time: 00:00:00")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save recording:\n{str(e)}")
            self.is_recording = False
            self.record_start_button.config(state='normal')
            self.record_stop_button.config(state='disabled')
    
    def recording_callback(self, indata, frames, time_info, status):
        if status:
            print(f"Status: {status}")
        
        if self.is_recording:
            self.recording_data.append(indata.copy())
    
    def update_recording_time(self):
        if not self.is_recording:
            return
        
        elapsed = time.time() - self.recording_start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        
        time_str = f"Time: {hours:02d}:{minutes:02d}:{seconds:02d}"
        self.recording_time_var.set(time_str)
        
        self.recording_timer_id = self.root.after(1000, self.update_recording_time)
    
    def show_recording_complete_dialog(self, filename):
        dialog = tk.Toplevel(self.root)
        dialog.title("Recording Complete")
        dialog.geometry("450x300")
        dialog.resizable(False, False)
        
        dialog.transient(self.root)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        message_frame = ttk.Frame(main_frame)
        message_frame.pack(fill=tk.X, expand=False, pady=5)
        
        ttk.Label(message_frame, text="✅", font=("", 24)).pack(pady=3)
        ttk.Label(message_frame, text="Recorded Successfully", 
                 font=("", 12, "bold")).pack(pady=3)
        ttk.Label(message_frame, text=f"Saved:\n{filename}\n\nClick 'Start Transcription' to proceed.",
                 justify=tk.CENTER).pack(pady=3)
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        dont_show_var = tk.BooleanVar(value=False)
        check_frame = ttk.Frame(main_frame)
        check_frame.pack(fill=tk.X, pady=5)
        
        ttk.Checkbutton(check_frame, text="✓ Don't show this again", 
                       variable=dont_show_var).pack(anchor=tk.W, padx=10)
        
        def on_ok():
            if dont_show_var.get():
                self.show_recording_complete_message = False
                self.config['show_recording_complete_message'] = False
                self.save_config()
            dialog.destroy()
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ok_button = ttk.Button(button_frame, text="OK", command=on_ok, width=15)
        ok_button.pack(pady=5)
        ok_button.focus_set()
        
        dialog.bind('<Return>', lambda e: on_ok())
        dialog.bind('<Escape>', lambda e: on_ok())
        dialog.protocol("WM_DELETE_WINDOW", on_ok)
    
    def start_transcription(self):
        input_method = self.audio_input_method_var.get()
        
        if input_method == 'file':
            file_paths = filedialog.askopenfilenames(
                title="Select Audio Files",
                filetypes=[
                    ("Audio Files", "*.mp3 *.wav *.m4a *.flac *.ogg *.mp4 *.mkv *.avi"),
                    ("All Files", "*.*")
                ]
            )
        else:  # mic
            recording_dir = self.recording_output_dir_var.get()
            file_paths = filedialog.askopenfilenames(
                title="Select Recording",
                initialdir=recording_dir,
                filetypes=[
                    ("Audio Files", "*.mp3 *.wav *.m4a *.flac *.ogg"),
                    ("All Files", "*.*")
                ]
            )
        
        if not file_paths:
            return
        
        self.selected_audio_files = file_paths
        
        self.transcribe_button.config(state='disabled')
        self.transcribe_stop_button.config(state='normal')
        self.transcription_result.delete('1.0', tk.END)
        
        threading.Thread(target=self._transcribe_worker, daemon=True).start()
    
    def _transcribe_worker(self):
        try:
            from datetime import datetime
            
            if not self.whisper_engine or \
               self.whisper_engine.model_size != self.whisper_model_var.get():
                self.root.after(0, lambda: self.transcription_result.insert(
                    tk.END, "🔧 Initializing Whisper Engine...\n"))
                self.root.after(0, lambda: self.transcription_result.see(tk.END))
                
                self.whisper_engine = WhisperEngine(
                    model_size=self.whisper_model_var.get(),
                    device='auto'
                )
            
            language = self.whisper_language_var.get().split(' - ')[0]
            output_format = self.whisper_format_var.get()
            total_files = len(self.selected_audio_files)
            
            all_results = []
            success_count = 0
            failed_files = []
            
            for i, file_path in enumerate(self.selected_audio_files, 1):
                file_path = Path(file_path)
                
                self.root.after(0, lambda i=i, t=total_files, n=file_path.name: 
                              self.transcription_result.insert(tk.END, f"\n[{i}/{t}] {n}\n"))
                self.root.after(0, lambda: self.transcription_result.see(tk.END))
                
                try:
                    def progress_callback(message):
                        self.root.after(0, lambda m=message: self.transcription_result.insert(tk.END, f"  {m}\n"))
                        self.root.after(0, lambda: self.transcription_result.see(tk.END))
                    
                    result = self.whisper_engine.transcribe(
                        file_path,
                        language=language,
                        output_format=output_format,
                        progress_callback=progress_callback
                    )
                    
                    all_results.append(result)
                    success_count += 1
                    
                    self.root.after(0, lambda: self.transcription_result.insert(tk.END, "✅ Done\n"))
                    
                except Exception as e:
                    failed_files.append(f"{file_path.name}: {str(e)}")
                    self.root.after(0, lambda e=e: self.transcription_result.insert(
                        tk.END, f"❌ Error: {str(e)}\n"))
            
            combined_result = "\n\n".join(all_results)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            first_text = combined_result[:20].strip()
            safe_text = "".join([c for c in first_text if c.isalnum() or c in (' ', '_', '-')]).replace(' ', '_')[:20]
            
            ext = "srt" if output_format == "srt" else "txt"
            
            if safe_text:
                filename = f"{timestamp}_{safe_text}.{ext}"
            else:
                filename = f"{timestamp}.{ext}"
            
            output_dir = Path(self.stt_output_dir_var.get())
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / filename
            
            counter = 1
            while output_file.exists():
                if safe_text:
                    filename = f"{timestamp}_{safe_text}_{counter}.{ext}"
                else:
                    filename = f"{timestamp}_{counter}.{ext}"
                output_file = output_dir / filename
                counter += 1
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(combined_result)
            
            self.root.after(0, lambda: self.transcription_result.insert(tk.END, "\n" + "="*60 + "\n"))
            self.root.after(0, lambda: self.transcription_result.insert(tk.END, "✅ Transcription Complete\n"))
            self.root.after(0, lambda: self.transcription_result.insert(tk.END, "="*60 + "\n\n"))
            
            summary = f"Processed: {success_count}/{total_files} Files\n"
            if failed_files:
                summary += f"Failed: {len(failed_files)}\n"
                for failed in failed_files:
                    summary += f"  - {failed}\n"
            summary += f"\n💾 Saved to: {output_file}\n\n"
            
            self.root.after(0, lambda s=summary: self.transcription_result.insert(tk.END, s))
            self.root.after(0, lambda: self.transcription_result.insert(tk.END, "="*60 + "\n\n"))
            self.root.after(0, lambda: self.transcription_result.insert(tk.END, combined_result))
            self.root.after(0, lambda: self.transcription_result.see(tk.END))
            
            if self.config.get('show_transcription_complete', True):
                self.root.after(0, lambda: self._show_transcription_complete())
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.root.after(0, lambda msg=error_msg: self.transcription_result.insert(tk.END, f"\n❌ {msg}\n"))
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("Error", msg))
        finally:
            self.root.after(0, lambda: self.transcribe_button.config(state='normal'))
            self.root.after(0, lambda: self.transcribe_stop_button.config(state='disabled'))
    
    def stop_transcription(self):
        messagebox.showinfo("Info", "Stop function coming in next update")
    
    def _show_transcription_complete(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Complete")
        dialog.geometry("450x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="✅ Transcription Complete", 
                 font=("", 12, "bold")).pack(pady=10)
        
        ttk.Label(dialog, text="Transfer result to TTS tab?").pack(pady=10)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def on_yes():
            self.transfer_to_generation()
            dialog.destroy()
        
        def on_no():
            dialog.destroy()
        
        ttk.Button(button_frame, text="Yes", command=on_yes, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="No", command=on_no, width=10).pack(side=tk.LEFT, padx=5)
        
        dont_show_var = tk.BooleanVar()
        ttk.Checkbutton(dialog, text="Don't show this again", 
                       variable=dont_show_var).pack(pady=10)
        
        info_label = ttk.Label(dialog, 
                              text="* Use 'Restore Popups' to enable again",
                              font=("", 8), foreground="blue")
        info_label.pack(pady=5)
        
        def on_close():
            if dont_show_var.get():
                self.config['show_transcription_complete'] = False
                self.save_config()
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_close)
    
    def transfer_to_generation(self):
        full_result = self.transcription_result.get('1.0', tk.END)
        
        if "✅ Transcription Complete" in full_result:
            result = full_result.split("="*60)[-1].strip()
        else:
            result = full_result.strip()
        
        if self._is_srt_format(result):
            result = self._extract_text_from_srt(result)
        
        if result:
            self.notebook.select(1)
            
            self.text_input.delete('1.0', tk.END)
            self.text_input.insert('1.0', result)
            
            messagebox.showinfo("Done", "Transferred text to TTS tab.\n(SRT timestamps removed automatically)")
    
    def _is_srt_format(self, text):
        lines = text.strip().split('\n')
        if len(lines) < 3:
            return False
        
        try:
            int(lines[0].strip())
            return '-->' in lines[1]
        except:
            return False
    
    def _extract_text_from_srt(self, srt_text):
        lines = srt_text.strip().split('\n')
        text_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.isdigit():
                i += 1
                continue
            
            if '-->' in line:
                i += 1
                continue
            
            if not line:
                i += 1
                continue
            
            text_lines.append(line)
            i += 1
        
        return '\n\n'.join(text_lines)
    
    def save_transcription_result(self):
        full_result = self.transcription_result.get('1.0', tk.END)
        
        if "✅ Transcription Complete" in full_result:
            result = full_result.split("="*60)[-1].strip()
        else:
            result = full_result.strip()
        
        if not result:
            messagebox.showwarning("Warning", "No content to save")
            return
        
        default_ext = ".txt" if self.whisper_format_var.get() == 'text' else ".srt"
        
        file_path = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension=default_ext,
            filetypes=[
                ("Text File", "*.txt"),
                ("SRT Subtitle", "*.srt"),
                ("All Files", "*.*")
            ]
        )
        
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(result)
            messagebox.showinfo("Saved", f"File saved:\n{file_path}")
    
    def open_stt_output_dir(self):
        path = Path(self.stt_output_dir_var.get())
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    
    def browse_stt_output_dir(self):
        current_dir = self.stt_output_dir_var.get()
        if not current_dir:
            current_dir = str(self.app_data / 'outputs')
        
        selected_dir = self.browse_folder_with_file_preview(
            title="Select STT Output Folder",
            initialdir=current_dir
        )
        
        if selected_dir:
            self.stt_output_dir_var.set(selected_dir)
    
    def browse_recording_output_dir(self):
        current_dir = self.recording_output_dir_var.get()
        if not current_dir:
            current_dir = str(self.app_data / 'recordings')
        
        selected_dir = self.browse_folder_with_file_preview(
            title="Select Recording Folder",
            initialdir=current_dir
        )
        
        if selected_dir:
            self.recording_output_dir_var.set(selected_dir)
    
    def open_recording_output_dir(self):
        path = Path(self.recording_output_dir_var.get())
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])


    
    # ==========================================
    # v2.2 Presets
    # ==========================================
    
    def build_preset_ui(self, parent):
        preset_frame = ttk.LabelFrame(parent, text="💾 Presets", padding="5")
        preset_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(preset_frame, text="Preset:").pack(side=tk.LEFT, padx=5)
        
        preset_combo = ttk.Combobox(preset_frame, textvariable=self.current_preset,
                                    values=list(self.presets.keys()),
                                    state='readonly', width=20)
        preset_combo.pack(side=tk.LEFT, padx=5)
        preset_combo.bind('<<ComboboxSelected>>', lambda e: self.load_preset())
        
        ttk.Button(preset_frame, text="💾 Save", command=self.save_preset, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="📝 Rename", command=self.rename_preset, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="🗑️ Del", command=self.delete_preset, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="➕ New", command=self.new_preset, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="❓", command=self.show_preset_help, width=3).pack(side=tk.LEFT, padx=2)
    
    def show_preset_help(self):
        messagebox.showinfo(
            "Preset Help",
            "【What is a Preset?】\n"
            "Save frequently used settings (speed, volume, speaker, etc.)\n"
            "and recall them with a single click.\n\n"
            "【How to use】\n"
            "1. Adjust settings (Speed, Volume, Character)\n"
            "2. Click '➕ New'\n"
            "3. Enter a name (e.g. 'Narration')\n"
            "4. Select from the dropdown to apply!\n\n"
            "【Default Preset】\n"
            "Contains initial settings:\n"
            "・Engine: Coqui TTS\n"
            "・Speed: 1.0, Volume: 1.0\n"
            "・Format: WAV\n\n"
            "【Examples】\n"
            "・Fast Narration (Speed 1.2)\n"
            "・Slow Reading (Speed 0.8)\n"
            "・Zundamon Main (VOICEVOX specific)"
        )
    
    def _get_current_settings(self):
        settings = {
            'engine': self.engine_var.get(),
            'speed': self.speed_var.get(),
            'volume': self.volume_var.get(),
            'pitch': self.pitch_var.get(),
            'intonation': self.intonation_var.get(),
            'pre_silence': self.pre_silence_var.get(),
            'post_silence': self.post_silence_var.get(),
            'format': self.format_var.get(),
            'prefix': self.prefix_var.get()
        }
        
        if hasattr(self, 'coqui_speaker_var'):
            settings['coqui_speaker'] = self.coqui_speaker_var.get()
        if hasattr(self, 'language_var'):
            settings['language'] = self.language_var.get()
        
        if hasattr(self, 'vv_speaker_var'):
            settings['voicevox_speaker'] = self.vv_speaker_var.get()
            settings['voicevox_speaker_id'] = self.get_speaker_id()
        
        return settings
    
    def _apply_settings(self, settings):
        self.engine_var.set(settings.get('engine', 'coqui'))
        self.update_ui_state()
        
        if settings.get('coqui_speaker'):
            self.coqui_speaker_var.set(settings['coqui_speaker'])
        if settings.get('language'):
            self.language_var.set(settings['language'])
        
        if settings.get('voicevox_speaker'):
            self.vv_speaker_var.set(settings['voicevox_speaker'])
        
        self.speed_var.set(settings.get('speed', 1.0))
        self.volume_var.set(settings.get('volume', 1.0))
        self.pitch_var.set(settings.get('pitch', 0.0))
        self.intonation_var.set(settings.get('intonation', 1.0))
        self.pre_silence_var.set(settings.get('pre_silence', 0.1))
        self.post_silence_var.set(settings.get('post_silence', 0.1))
        self.format_var.set(settings.get('format', 'wav'))
        self.prefix_var.set(settings.get('prefix', 'voice'))
    
    def save_preset(self):
        preset_name = self.current_preset.get()
        if not preset_name:
            messagebox.showwarning("Warning", "Please select a preset name")
            return
        
        self.presets[preset_name] = self._get_current_settings()
        self.config['presets'] = self.presets
        self.save_config()
        messagebox.showinfo("Saved", f"Preset '{preset_name}' saved.")
    
    def load_preset(self):
        preset_name = self.current_preset.get()
        if preset_name not in self.presets:
            return
        
        settings = self.presets[preset_name]
        self._apply_settings(settings)
        self.status_bar.config(text=f"Preset '{preset_name}' loaded.")
    
    def new_preset(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("New Preset")
        dialog.geometry("350x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Preset Name:").pack(pady=10)
        
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        name_entry.pack(pady=5)
        name_entry.focus()
        
        def on_ok():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Warning", "Enter a name")
                return
            if name in self.presets:
                if not messagebox.askyesno("Confirm", f"'{name}' exists. Overwrite?"):
                    return
            
            self.presets[name] = self._get_current_settings()
            self.current_preset.set(name)
            self.config['presets'] = self.presets
            self.save_config()
            dialog.destroy()
            messagebox.showinfo("Done", f"Preset '{name}' created.")
            
            for widget in self.root.winfo_children():
                self._update_preset_combo(widget, list(self.presets.keys()))
        
        ttk.Button(dialog, text="OK", command=on_ok, width=15).pack(pady=10)
    
    def _update_preset_combo(self, widget, values):
        if isinstance(widget, ttk.Combobox) and widget.cget('textvariable') == str(self.current_preset):
            widget['values'] = values
        for child in widget.winfo_children():
            self._update_preset_combo(child, values)
    
    def rename_preset(self):
        old_name = self.current_preset.get()
        if old_name == 'Default':
            messagebox.showwarning("Warning", "Default preset cannot be renamed")
            return
        if old_name not in self.presets:
            messagebox.showwarning("Warning", "Select a preset")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Rename Preset")
        dialog.geometry("350x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="New Name:").pack(pady=10)
        
        name_var = tk.StringVar(value=old_name)
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        name_entry.pack(pady=5)
        name_entry.focus()
        name_entry.select_range(0, tk.END)
        
        def on_ok():
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showwarning("Warning", "Enter a name")
                return
            if new_name in self.presets and new_name != old_name:
                messagebox.showwarning("Warning", f"'{new_name}' already exists")
                return
            
            self.presets[new_name] = self.presets.pop(old_name)
            self.current_preset.set(new_name)
            self.config['presets'] = self.presets
            self.save_config()
            dialog.destroy()
            messagebox.showinfo("Done", f"Renamed '{old_name}' to '{new_name}'.")
            
            for widget in self.root.winfo_children():
                self._update_preset_combo(widget, list(self.presets.keys()))
        
        ttk.Button(dialog, text="OK", command=on_ok, width=15).pack(pady=10)
    
    def delete_preset(self):
        preset_name = self.current_preset.get()
        if preset_name == 'Default':
            messagebox.showwarning("Warning", "Default preset cannot be deleted")
            return
        if preset_name not in self.presets:
            messagebox.showwarning("Warning", "Select a preset")
            return
        
        if messagebox.askyesno("Confirm", f"Delete preset '{preset_name}'?"):
            del self.presets[preset_name]
            self.current_preset.set('Default')
            self.config['presets'] = self.presets
            self.save_config()
            messagebox.showinfo("Done", f"Deleted '{preset_name}'.")
            
            for widget in self.root.winfo_children():
                self._update_preset_combo(widget, list(self.presets.keys()))
    
    # ==========================================
    # v2.2 Voice Preview
    # ==========================================
    
    def preview_voice(self):
        try:
            full_text = self.text_input.get('1.0', tk.END).strip()
            if not full_text:
                messagebox.showwarning("Warning", "Please enter text")
                return
            
            preview_text = full_text[:30].strip()
            if not preview_text:
                return
            
            self.status_bar.config(text="🔊 Generating Preview...")
            self.root.update()
            
            engine = self.engine_var.get()
            speed = self.speed_var.get()
            
            if engine == 'voicevox':
                wav_bytes = self.run_voicevox(preview_text)
            else:
                wav_bytes = self.run_coqui(preview_text, speed)
            
            volume = self.volume_var.get()
            pre_sil = self.pre_silence_var.get()
            post_sil = self.post_silence_var.get()
            audio = self.post_process_audio(wav_bytes, volume, pre_sil, post_sil)
            
            temp_file = self.app_data / "preview_temp.wav"
            audio.export(temp_file, format="wav")
            
            self._play_audio(temp_file)
            self.status_bar.config(text="✓ Preview Played")
            
        except Exception as e:
            messagebox.showerror("Error", f"Preview Failed:\n{str(e)}")
            self.status_bar.config(text="✗ Preview Failed")
    
    def _play_audio(self, audio_path):
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(audio_path)
            elif system == "Darwin":
                subprocess.Popen(["afplay", str(audio_path)])
            else:
                subprocess.Popen(["aplay", str(audio_path)])
        except Exception as e:
            messagebox.showerror("Error", f"Playback failed:\n{str(e)}")
    
    def show_preview_help(self):
        messagebox.showinfo(
            "Preview Help",
            "【What is Preview?】\n"
            "Generates and plays only the first 30 characters\n"
            "to quickly test your settings.\n\n"
            "【Features】\n"
            "・Fast: Takes ~3 seconds (Full text might take 30s+)\n"
            "・Range: First 30 chars only\n"
            "・Test: Speed, Pitch, Speaker settings apply\n"
            "・No Save: Files are temporary (not saved to output)\n\n"
            "【Usage】\n"
            "1. Enter text (Full text is fine)\n"
            "2. Adjust settings\n"
            "3. Click '🔊 Preview'\n"
            "4. Listen & Tweak\n"
            "5. Click '🎵 Start Generation' when ready"
        )
    
    # ==========================================
    # v2.2 Batch Processing (STT)
    # ==========================================
    
    def batch_transcribe(self):
        # ... (Redundant with new STT tab logic, keeping for compatibility if referenced)
        pass
    
    # ==========================================
    # v2.2 Batch Processing (TTS)
    # ==========================================
    
    def batch_generate(self):
        folder_path = self.browse_folder_with_file_preview(
            title="Select Folder with Text Files"
        )
        
        if not folder_path:
            return
        
        folder_path = Path(folder_path)
        all_txt_files = list(folder_path.glob("*.txt"))
        txt_files = [f for f in all_txt_files if not f.name.endswith('_log.txt')]
        
        if not txt_files:
            messagebox.showwarning(
                "Warning", 
                f"No .txt files found in:\n{folder_path}\n\n"
                f"* Log files (_log.txt) are excluded."
            )
            return
        
        if not messagebox.askyesno("Confirm", 
            f"Found {len(txt_files)} text files.\n\n"
            f"Load them into the input area?\n"
            f"(Current text will be overwritten)"):
            return
        
        all_texts = []
        for txt_file in sorted(txt_files):
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                if text:
                    all_texts.append(text)
            except Exception as e:
                messagebox.showerror("Error", f"Read error:\n{txt_file.name}\n{str(e)}")
                return
        
        if not all_texts:
            messagebox.showwarning("Warning", "No text content found.")
            return
        
        self.text_input.delete('1.0', tk.END)
        combined_text = '\n\n'.join(all_texts)
        self.text_input.insert('1.0', combined_text)
        
        segment_count = len(all_texts)
        self.status_bar.config(text=f"✓ Loaded {len(txt_files)} files ({segment_count} segments)")
        
        messagebox.showinfo(
            "Loaded", 
            f"✅ Loaded {len(txt_files)} files\n"
            f"📝 {segment_count} segments (separated by blank lines)\n\n"
            f"Check the text input area, then click '🎵 Start Generation'."
        )

    
    # ==========================================
    # v2.2 Text History
    # ==========================================
    
    def save_to_history(self, text):
        text = text.strip()
        if not text or len(text) < 5:
            return
        
        if text in self.text_history:
            self.text_history.remove(text)
        
        self.text_history.insert(0, text)
        self.text_history = self.text_history[:10]
        self.config['text_history'] = self.text_history
        self.save_config()
    
    def show_text_history(self):
        if not self.text_history:
            messagebox.showinfo("History", "No history yet.")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Text History")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Recent Text (Double click to apply)", 
                 font=("", 10, "bold")).pack(pady=10)
        
        listbox = tk.Listbox(dialog, height=15, font=("", 9))
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        for item in self.text_history:
            preview = item[:60] + "..." if len(item) > 60 else item
            listbox.insert(tk.END, preview)
        
        def on_select(event):
            if not listbox.curselection():
                return
            index = listbox.curselection()[0]
            text = self.text_history[index]
            self.text_input.delete('1.0', tk.END)
            self.text_input.insert('1.0', text)
            dialog.destroy()
            messagebox.showinfo("Applied", "History text applied.")
        
        listbox.bind('<Double-Button-1>', on_select)
        
        ttk.Button(dialog, text="Close", command=dialog.destroy, width=10).pack(pady=10)
    
    # ==========================================
    # v2.2 Templates
    # ==========================================
    
    def save_template(self):
        text = self.text_input.get('1.0', tk.END).strip()
        if not text:
            messagebox.showwarning("Warning", "Enter text first")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Save Template")
        dialog.geometry("350x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Template Name:").pack(pady=10)
        
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        name_entry.pack(pady=5)
        name_entry.focus()
        
        def on_ok():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Warning", "Enter a name")
                return
            
            self.templates[name] = text
            self.config['templates'] = self.templates
            self.save_config()
            dialog.destroy()
            messagebox.showinfo("Saved", f"Template '{name}' saved.")
        
        ttk.Button(dialog, text="OK", command=on_ok, width=15).pack(pady=10)
    
    def load_template(self):
        if not self.templates:
            messagebox.showinfo("Templates", "No templates saved.")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Load Template")
        dialog.geometry("500x350")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Templates (Double click to apply)", 
                 font=("", 10, "bold")).pack(pady=10)
        
        listbox = tk.Listbox(dialog, height=12, font=("", 9))
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        for name in self.templates.keys():
            listbox.insert(tk.END, name)
        
        def on_select(event):
            if not listbox.curselection():
                return
            index = listbox.curselection()[0]
            name = list(self.templates.keys())[index]
            text = self.templates[name]
            self.text_input.delete('1.0', tk.END)
            self.text_input.insert('1.0', text)
            dialog.destroy()
            messagebox.showinfo("Applied", f"Template '{name}' applied.")
        
        listbox.bind('<Double-Button-1>', on_select)
        
        # Button frame
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def delete_selected():
            """Delete selected template"""
            if not listbox.curselection():
                messagebox.showwarning("Warning", "Please select a template to delete")
                return
            
            index = listbox.curselection()[0]
            name = list(self.templates.keys())[index]
            
            # Confirm deletion
            result = messagebox.askyesno(
                "Confirm Deletion",
                f"Delete template '{name}'?"
            )
            
            if result:
                # Execute deletion
                del self.templates[name]
                self.save_config()  # Save settings
                
                # Update Listbox
                listbox.delete(0, tk.END)
                for template_name in self.templates.keys():
                    listbox.insert(tk.END, template_name)
                
                messagebox.showinfo("Deleted", f"Template '{name}' deleted")
                
                # Close dialog if no templates remain
                if not self.templates:
                    messagebox.showinfo("Templates", "All templates deleted")
                    dialog.destroy()
        
        ttk.Button(button_frame, text="🗑️ Delete", command=delete_selected, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
    
    def show_template_help(self):
        messagebox.showinfo(
            "Template Help",
            "【What is a Template?】\n"
            "Save frequently used text (Intro, Outro, etc.)\n"
            "and recall it with a single click.\n\n"
            "【Difference from Preset】\n"
            "・Preset = 'How to read' (Settings)\n"
            "・Template = 'What to read' (Text content)\n\n"
            "【Usage】\n"
            "1. Enter text in the main box\n"
            "2. Click '💾' (Save Template)\n"
            "3. Enter a name (e.g., Intro)\n"
            "4. To use: Click '📝 Templates' and select."
        )
    
    # ==========================================
    # v2.2 Auto Backup
    # ==========================================
    
    def start_auto_backup(self):
        if self.auto_backup_enabled:
            self.auto_backup()
            self.backup_timer_id = self.root.after(60000, self.start_auto_backup)
    
    def auto_backup(self):
        try:
            text = self.text_input.get('1.0', tk.END).strip()
            if text and len(text) > 10:
                backup_file = self.app_data / "text_backup.txt"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(text)
        except:
            pass
    
    def restore_backup(self):
        backup_file = self.app_data / "text_backup.txt"
        
        if not backup_file.exists():
            messagebox.showinfo("Backup", "No backup found")
            return
        
        if messagebox.askyesno("Confirm", "Restore from backup?\nCurrent text will be overwritten"):
            with open(backup_file, 'r', encoding='utf-8') as f:
                text = f.read()
            self.text_input.delete('1.0', tk.END)
            self.text_input.insert('1.0', text)
            messagebox.showinfo("Restored", "Backup restored")


if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    root = tk.Tk()
    style = ttk.Style()
    if 'vista' in style.theme_names(): style.theme_use('vista')
    app = VoicevoxCoquiGUI(root)
    try:
        if 'pyi_splash' in sys.modules and pyi_splash.is_alive(): pyi_splash.close()
    except NameError: pass
    root.mainloop()