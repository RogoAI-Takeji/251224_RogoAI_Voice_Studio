"""
RogoAI Voice Studio - 最終完全版 v1.9.2 (Build Script)
修正内容:
1. Step 1 バッチファイルの文字化け修正 (chcp 65001削除)
2. GUIバグ修正: VOICEVOX選択時にCoqui設定行が消えない問題を解消 (pack_forget)
3. バージョン表記と出力ファイル名を v1.9.2 に更新 (JP/EN共通)
4. ★追加修正: EN版作成時に日本語UIを英語に自動置換する機能を追加
"""
import os
import shutil
from pathlib import Path

# ==========================================
# 基本設定
# ==========================================
BASE_NAME = "RogoAI_Voice_Studio"
VERSION = "v1.9.2"
DIST_ROOT = "dist"

# requirements.txt の内容
REQUIREMENTS_CONTENT = """TTS==0.22.0
requests
Pillow
soundfile
librosa
numpy
inflect
pysbd
gruut[de,es,fr]==2.2.3
anyascii
jamo
pypinyin
jieba
mecab-python3
unidic-lite
cutlet
g2pkk
bangla
bnnumerizer
bnunicodenormalizer
transformers==4.33.0
"""

# ==========================================
# アプリケーション本体のコード (JPベース)
# ==========================================
APP_SCRIPT_CONTENT = r'''
"""
ROGOAI Voice Studio v1.9.2 JP Slim
Universal Voice Generation Platform

機能:
1. VOICEVOXキャラクター音声生成
2. Coqui TTS XTTS Zero-Shot Voice Cloning
3. GUI刷新: スリム化＆カスタムファイル名命名機能
4. 安全な非同期起動処理
5. JP/EN展開を見据えたUI調整

Author: ROGOAI
Version: 1.9.2 JP Slim (GUI Fix)
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

# ==========================================
# PyTorch互換性パッチ
# ==========================================
import torch
_original_load = torch.load
def _patched_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = _patched_load

CUDA_AVAILABLE = torch.cuda.is_available()
CUDA_DEVICE = torch.cuda.get_device_name(0) if CUDA_AVAILABLE else "CPU"
# ==========================================

def setup_ffmpeg():
    base_path = Path(__file__).parent
    ffmpeg_exe = base_path / "ffmpeg" / "ffmpeg.exe"
    ffprobe_exe = base_path / "ffmpeg" / "ffprobe.exe"
    
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
        self.root.title(f"🎙️ ROGOAI Voice Studio v1.9.2 JP - {gpu_status}")

        try:
            icon_path = Path(__file__).parent / "make_icon" / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except:
            pass
        
        self.root.geometry("680x860")
        
        self.app_data = self.get_app_data_path()
        self.voicevox_server_url = "http://127.0.0.1:50021"
        
        self.coqui_enabled = False
        self.coqui_model = None
        self.samples_dir = self.app_data / "samples"
        self.samples_dir.mkdir(parents=True, exist_ok=True)
        
        self.generation_stop_flag = False
        self.config_file = self.app_data / "config.json"
        self.load_config()
        
        self.voicevox_speakers = []
        self.build_gui()
        self.initialize_app_async()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def get_app_data_path(self):
        if getattr(sys, 'frozen', False):
            base = Path(os.path.dirname(sys.executable))
        else:
            base = Path(os.path.dirname(os.path.abspath(__file__)))
        
        app_path = base / 'user_data'
        app_path.mkdir(parents=True, exist_ok=True)
        (app_path / 'outputs').mkdir(exist_ok=True)
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
                self.root.after(0, lambda: messagebox.showerror("起動エラー", f"初期化中にエラーが発生しました:\n{e}"))

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
            self.root.after(0, lambda m=f"📥 DL中: {fname}...": self.status_bar.config(text=m))
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                with open(save_path, 'wb') as f: f.write(response.content)
        except: pass

    def initialize_coqui(self):
        if self.coqui_model: return
        try:
            self.root.after(0, lambda: self.coqui_status_label.config(text="Coqui TTS: 起動処理中...", foreground="orange"))
            self.root.after(0, lambda: self.status_bar.config(text="🚀 AIエンジンを読み込んでいます（数秒待ちます）..."))
            
            from TTS.api import TTS
            self.coqui_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
            if CUDA_AVAILABLE: self.coqui_model.to("cuda")
            self.coqui_enabled = True
            
            self.root.after(0, lambda: self.coqui_status_label.config(text="Coqui TTS: 準備完了", foreground="green"))
            self.root.after(0, lambda: self.status_bar.config(text="✓ Coqui TTSエンジンの準備が整いました"))
            
        except Exception as e:
            self.root.after(0, lambda: self.coqui_status_label.config(text="Coqui TTS: 起動失敗", foreground="red"))
            err_msg = str(e)
            print(f"Coqui Init Error: {err_msg}")
            self.root.after(0, lambda: messagebox.showerror("AIエンジン起動エラー", f"Coqui TTSの起動に失敗しました。\n\nエラー内容:\n{err_msg}"))

    def build_gui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tab_tts = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tts, text="🗣️ TTS (音声合成)")
        self.build_tts_tab(self.tab_tts)

    def build_tts_tab(self, parent):
        main_frame = ttk.Frame(parent, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. サーバー状態
        status_frame = ttk.LabelFrame(main_frame, text="サーバー・エンジン状態", padding="2")
        status_frame.pack(fill=tk.X, pady=2)
        
        self.coqui_status_label = ttk.Label(status_frame, text="Coqui TTS: 起動処理中...", foreground="orange")
        self.coqui_status_label.pack(side=tk.LEFT, padx=10)
        ttk.Label(status_frame, text="|").pack(side=tk.LEFT, padx=5)

        self.voicevox_status_label = ttk.Label(status_frame, text="VOICEVOX: 確認中...")
        self.voicevox_status_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(status_frame, text="🔄 再接続", command=self.reconnect_voicevox_async, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(status_frame, text="＊再接続のためVOICEVOXを起動してください", font=("", 8), foreground="gray").pack(side=tk.LEFT, padx=5)
        
        # 2. エンジン選択
        engine_frame = ttk.LabelFrame(main_frame, text="🎙️ 音声生成エンジン選択", padding="2")
        engine_frame.pack(fill=tk.X, pady=2)
        
        default_engine = self.config.get('engine', 'coqui') 
        self.engine_var = tk.StringVar(value=default_engine)
        
        ttk.Radiobutton(engine_frame, text="Coqui TTS XTTS (ファイル参照型)", variable=self.engine_var, value="coqui", command=self.update_ui_state).pack(side=tk.LEFT, padx=15)
        ttk.Radiobutton(engine_frame, text="VOICEVOX (内蔵キャラ型)", variable=self.engine_var, value="voicevox", command=self.update_ui_state).pack(side=tk.LEFT, padx=15)

        # 3. キャラクター設定エリア
        self.char_frame = ttk.LabelFrame(main_frame, text="👤 話者設定", padding="2")
        self.char_frame.pack(fill=tk.X, pady=2)

        # --- Coqui TTS用 UI ---
        self.coqui_container = ttk.Frame(self.char_frame)
        ttk.Label(self.coqui_container, text="話者ファイル:").grid(row=0, column=0, sticky=tk.W, padx=(5,2))
        
        self.coqui_speaker_var = tk.StringVar()
        self.coqui_speaker_combo = ttk.Combobox(self.coqui_container, textvariable=self.coqui_speaker_var, width=30, state="readonly")
        self.coqui_speaker_combo.grid(row=0, column=1, padx=2)
        
        ttk.Button(self.coqui_container, text="音声フォルダ", command=self.open_samples_dir, width=12).grid(row=0, column=2, padx=2)
        ttk.Button(self.coqui_container, text="再適用", command=self.refresh_coqui_speakers, width=8).grid(row=0, column=3, padx=2)
        
        ttk.Label(self.coqui_container, text="言語:").grid(row=0, column=4, sticky=tk.W, padx=(10, 2))
        self.language_var = tk.StringVar(value=self.config.get('language', 'ja'))
        self.language_combo = ttk.Combobox(self.coqui_container, textvariable=self.language_var, width=8, state="readonly")
        self.language_combo['values'] = ['ja - 日', 'en - 英', 'zh-cn - 中', 'ko - 韓', 'fr - 仏', 'de - 独']
        self.language_combo.current(0)
        self.language_combo.grid(row=0, column=5, padx=2)

        # --- VOICEVOX用 UI ---
        self.vv_container = ttk.Frame(self.char_frame)
        ttk.Label(self.vv_container, text="キャラクター:").pack(side=tk.LEFT)
        self.vv_speaker_var = tk.StringVar()
        self.vv_speaker_combo = ttk.Combobox(self.vv_container, textvariable=self.vv_speaker_var, width=40, state="readonly")
        self.vv_speaker_combo.pack(side=tk.LEFT, padx=5)

        # 4. パラメータ設定
        params_container = ttk.Frame(main_frame)
        params_container.pack(fill=tk.X, pady=2)
        
        param_frame = ttk.LabelFrame(params_container, text="🎚️ 音声パラメータ設定 ([VV]: VOICEVOXのみ有効)", padding="2")
        param_frame.pack(fill=tk.X)

        COLOR_COMMON = "#d4edda"
        COLOR_VV = "#cce5ff"
        lbl_speed = tk.Label(param_frame, text="話速:", bg=COLOR_COMMON, padx=5)
        lbl_speed.grid(row=0, column=0, sticky=tk.W+tk.E, padx=2, pady=2)
        self.speed_var = tk.DoubleVar(value=self.config.get('speed', 1.0))
        tk.Scale(param_frame, from_=0.5, to=2.0, resolution=0.01, orient=tk.HORIZONTAL, variable=self.speed_var, showvalue=0, length=120, troughcolor=COLOR_COMMON, bg="#f0f0f0", bd=0).grid(row=0, column=1, padx=5)
        
        lbl_vol = tk.Label(param_frame, text="音量:", bg=COLOR_COMMON, padx=5)
        lbl_vol.grid(row=0, column=2, sticky=tk.W+tk.E, padx=2, pady=2)
        self.volume_var = tk.DoubleVar(value=self.config.get('volume', 1.0))
        tk.Scale(param_frame, from_=0.0, to=2.0, resolution=0.01, orient=tk.HORIZONTAL, variable=self.volume_var, showvalue=0, length=120, troughcolor=COLOR_COMMON, bg="#f0f0f0", bd=0).grid(row=0, column=3, padx=5)

        lbl_pitch = tk.Label(param_frame, text="音程 [VV]:", bg=COLOR_VV, padx=5)
        lbl_pitch.grid(row=1, column=0, sticky=tk.W+tk.E, padx=2, pady=2)
        self.pitch_var = tk.DoubleVar(value=self.config.get('pitch', 0.0))
        self.pitch_scale = tk.Scale(param_frame, from_=-0.15, to=0.15, resolution=0.01, orient=tk.HORIZONTAL, variable=self.pitch_var, showvalue=0, length=120, troughcolor=COLOR_VV, bg="#f0f0f0", bd=0)
        self.pitch_scale.grid(row=1, column=1, padx=5)

        lbl_int = tk.Label(param_frame, text="抑揚 [VV]:", bg=COLOR_VV, padx=5)
        lbl_int.grid(row=1, column=2, sticky=tk.W+tk.E, padx=2, pady=2)
        self.intonation_var = tk.DoubleVar(value=self.config.get('intonation', 1.0))
        self.intonation_scale = tk.Scale(param_frame, from_=0.0, to=2.0, resolution=0.01, orient=tk.HORIZONTAL, variable=self.intonation_var, showvalue=0, length=120, troughcolor=COLOR_VV, bg="#f0f0f0", bd=0)
        self.intonation_scale.grid(row=1, column=3, padx=5)

        silence_frame = ttk.LabelFrame(params_container, text="🔇 無音設定 (秒)", padding="2")
        silence_frame.pack(fill=tk.X, pady=2)
        ttk.Label(silence_frame, text="開始:").pack(side=tk.LEFT, padx=2)
        self.pre_silence_var = tk.DoubleVar(value=self.config.get('pre_silence', 0.1))
        ttk.Entry(silence_frame, textvariable=self.pre_silence_var, width=4).pack(side=tk.LEFT)
        ttk.Label(silence_frame, text="終了:").pack(side=tk.LEFT, padx=5)
        self.post_silence_var = tk.DoubleVar(value=self.config.get('post_silence', 0.1))
        ttk.Entry(silence_frame, textvariable=self.post_silence_var, width=4).pack(side=tk.LEFT)
        ttk.Label(silence_frame, text="句読点:").pack(side=tk.LEFT, padx=5)
        self.punctuation_silence_var = tk.DoubleVar(value=self.config.get('punctuation_silence', 0.3))
        ttk.Entry(silence_frame, textvariable=self.punctuation_silence_var, width=4).pack(side=tk.LEFT)

        # 5. テキスト入力
        text_frame = ttk.LabelFrame(main_frame, text="📝 テキスト入力", padding="2")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        tool_frame = ttk.Frame(text_frame)
        tool_frame.pack(fill=tk.X)
        
        ttk.Button(tool_frame, text="📂 読込", command=self.load_text_file, width=8).pack(side=tk.LEFT)
        tk.Button(tool_frame, text="🗑️ 消去", command=self.clear_text_input, bg="#dc3545", fg="white", font=("", 8, "bold"), relief=tk.RAISED, width=8).pack(side=tk.LEFT, padx=10)
        
        self.text_input = scrolledtext.ScrolledText(text_frame, width=60, height=5)
        self.text_input.pack(fill=tk.BOTH, expand=True)

        # 6. 出力設定
        output_frame = ttk.LabelFrame(main_frame, text="💾 出力設定", padding="5")
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(output_frame, text="出力先:").grid(row=0, column=0, sticky=tk.W, padx=5)
        default_output = self.config.get('output_dir', str(self.app_data / 'outputs'))
        self.output_dir_var = tk.StringVar(value=default_output)
        ttk.Entry(output_frame, textvariable=self.output_dir_var, width=30).grid(row=0, column=1, padx=5, columnspan=2, sticky=tk.W+tk.E)
        
        ttk.Button(output_frame, text="参照", command=self.browse_output_dir, width=5).grid(row=0, column=3, padx=2)
        ttk.Button(output_frame, text="開く", command=self.open_output_dir, width=5).grid(row=0, column=4, padx=2)
        
        ttk.Label(output_frame, text="形式:").grid(row=0, column=5, sticky=tk.W, padx=10)
        self.format_var = tk.StringVar(value=self.config.get('format', 'wav'))
        ttk.Combobox(output_frame, textvariable=self.format_var, values=['wav', 'mp3'], width=5, state="readonly").grid(row=0, column=6, sticky=tk.W, padx=2)

        ttk.Label(output_frame, text="接頭辞:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.prefix_var = tk.StringVar(value=self.config.get('prefix', 'voice'))
        ttk.Entry(output_frame, textvariable=self.prefix_var, width=15).grid(row=1, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(output_frame, text="連番桁:").grid(row=1, column=2, sticky=tk.E, padx=2)
        self.seq_digits_var = tk.IntVar(value=self.config.get('seq_digits', 3))
        ttk.Spinbox(output_frame, from_=1, to=10, textvariable=self.seq_digits_var, width=3).grid(row=1, column=3, sticky=tk.W, padx=2)

        ttk.Label(output_frame, text="命名規則:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.filename_pattern_var = tk.StringVar(value=self.config.get('filename_pattern', '{ID}_{接頭辞}_{連番}'))
        self.pattern_entry = ttk.Entry(output_frame, textvariable=self.filename_pattern_var)
        self.pattern_entry.grid(row=2, column=1, columnspan=5, sticky=tk.W+tk.E, padx=5)
        
        tag_frame = ttk.Frame(output_frame)
        tag_frame.grid(row=3, column=1, columnspan=5, sticky=tk.W, pady=2)
        
        def add_tag(tag):
            self.pattern_entry.insert(tk.INSERT, tag)
            
        ttk.Label(tag_frame, text="タグ挿入:", font=("", 8), foreground="gray").pack(side=tk.LEFT, padx=(5,5))
        ttk.Button(tag_frame, text="+文字(7)", command=lambda: add_tag("{文字}"), width=8).pack(side=tk.LEFT, padx=1)
        ttk.Button(tag_frame, text="+ID", command=lambda: add_tag("{ID}"), width=5).pack(side=tk.LEFT, padx=1)
        ttk.Button(tag_frame, text="+日時", command=lambda: add_tag("{日時}"), width=6).pack(side=tk.LEFT, padx=1)
        ttk.Button(tag_frame, text="+接頭辞", command=lambda: add_tag("{接頭辞}"), width=9).pack(side=tk.LEFT, padx=1)
        ttk.Button(tag_frame, text="+連番", command=lambda: add_tag("{連番}"), width=6).pack(side=tk.LEFT, padx=1)

        # 7. ボタン群
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        self.generate_button = tk.Button(button_frame, text="🎵 音声生成開始", command=self.generate_voice, bg="#28a745", fg="white", font=("", 12, "bold"), padx=15, pady=5, relief=tk.RAISED, cursor="hand2")
        self.generate_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = tk.Button(button_frame, text="⏹️ 生成停止", command=self.stop_generation, bg="#dc3545", fg="white", font=("", 12, "bold"), padx=15, pady=5, relief=tk.RAISED, cursor="hand2", state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔄 設定リセット", command=self.reset_settings).pack(side=tk.LEFT, padx=5)

        self.status_bar = ttk.Label(main_frame, text="準備完了", relief=tk.SUNKEN)
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
        self.voicevox_status_label.config(text="VOICEVOX: 再接続中...", foreground="orange")
        threading.Thread(target=self._reconnect_voicevox, daemon=True).start()

    def _reconnect_voicevox(self):
        try:
            requests.get(f"{self.voicevox_server_url}/version", timeout=2)
            self.root.after(0, lambda: self.voicevox_status_label.config(text="VOICEVOX: 接続OK", foreground="green"))
            self.root.after(0, self.refresh_voicevox_speakers)
            self.root.after(0, lambda: messagebox.showinfo("成功", "VOICEVOXエンジンと接続しました！"))
        except:
            self.root.after(0, lambda: self.voicevox_status_label.config(text="VOICEVOX: 未接続", foreground="red"))

    # =======================================================
    # ★修正箇所: grid_forget -> pack_forget に変更 (v1.9.2)
    # =======================================================
    def update_ui_state(self):
        engine = self.engine_var.get()
        if engine == 'voicevox':
            self.vv_container.pack(fill=tk.X, expand=True)
            self.coqui_container.pack_forget()  # ★修正済み
            self.pitch_scale.config(state='normal', fg='black')
            self.intonation_scale.config(state='normal', fg='black')
        else:
            self.vv_container.pack_forget()
            self.coqui_container.pack(fill=tk.X, expand=True)
            self.pitch_scale.config(state='disabled', fg='gray')
            self.intonation_scale.config(state='disabled', fg='gray')
            if not self.coqui_speaker_combo['values']:
                self.refresh_coqui_speakers()
    # =======================================================

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
        if not options: options = ["(サンプルフォルダが空です)"]
        self.coqui_speaker_combo['values'] = options
        
        default_target = "de_female_official.wav"
        if default_target in options: self.coqui_speaker_combo.current(options.index(default_target))
        else: self.coqui_speaker_combo.current(0)

    def get_first_7_chars(self, text):
        clean_text = text.replace('\n', '').replace('\r', '').replace(' ', '').replace('　', '')
        return clean_text[:7] if len(clean_text) >= 7 else clean_text.ljust(7, '_')

    def load_text_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")])
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
        self.status_bar.config(text="設定をリセットしました")

    def clear_text_input(self):
        if messagebox.askyesno("確認", "消去しますか？"):
            self.text_input.delete(1.0, tk.END)

    def stop_generation(self):
        self.generation_stop_flag = True
        self.status_bar.config(text="⏹️ 停止処理中...")

    def generate_voice(self):
        text = self.text_input.get(1.0, tk.END).strip()
        if not text: return
        if self.engine_var.get() == 'coqui' and not self.coqui_enabled:
            messagebox.showwarning("準備中", "Coqui TTS起動中です。")
            return
        
        segments = [s.strip() for s in text.split('\n\n') if s.strip()]
        self.generation_stop_flag = False
        self.generate_button.config(state='disabled', text="🎵 生成中...")
        self.stop_button.config(state='normal')
        threading.Thread(target=self._generate_voice_async, args=(segments,), daemon=True).start()

    def generate_filename(self, speaker_id, index, extension, text="", engine="VOICEVOX"):
        pattern = self.filename_pattern_var.get()
        if not pattern: pattern = "{ID}_{接頭辞}_{連番}"
        
        prefix = self.prefix_var.get()
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        first_7 = self.get_first_7_chars(text)
        
        digits = self.seq_digits_var.get()
        seq_str = str(index).zfill(digits)
        
        if engine == "CoquiTTS": chara_id = "CQ"
        else: chara_id = f"{speaker_id:03d}"
        
        fname = pattern.replace("{文字}", first_7)
        fname = fname.replace("{ID}", f"ID{chara_id}")
        fname = fname.replace("{日時}", timestamp)
        fname = fname.replace("{接頭辞}", prefix)
        fname = fname.replace("{連番}", seq_str)
        
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
                
                self.root.after(0, lambda p=int((i-1)/len(segments)*100), c=i: self._update_progress(p, f"生成中: {c}/{len(segments)}"))
                
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
                count += 1
            
            self.root.after(0, lambda: self._update_progress(100, "完了！"))
            self.root.after(0, lambda: self._on_generation_complete(count, len(segments), output_dir))
        except Exception as e:
            traceback.print_exc()
            self.root.after(0, lambda: messagebox.showerror("エラー", str(e)))
        finally:
            self.root.after(0, lambda: self.generate_button.config(state='normal', text="🎵 音声生成開始"))
            self.root.after(0, lambda: self.stop_button.config(state='disabled'))
            self.root.after(0, self._close_progress_dialog)
            self.root.after(0, self.save_config)

    def _show_progress_dialog(self, total):
        self.progress_dialog = tk.Toplevel(self.root)
        self.progress_dialog.title("生成中")
        self.progress_dialog.geometry("400x120")
        ttk.Label(self.progress_dialog, text="音声を生成しています...", font=("", 11)).pack(pady=10)
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
        msg = f"生成完了: {count}/{total}ファイル\n保存先: {output_dir}"
        messagebox.showinfo("完了", msg)

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
        except: self.voicevox_status_label.config(text="VOICEVOX: 未接続", foreground="red")

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
        d = filedialog.askdirectory()
        if d: self.output_dir_var.set(d)

    def load_config(self):
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f: self.config = json.load(f)
        else: self.config = {}

    def save_config(self):
        try:
            self.config = {
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
                'language': self.language_var.get()
            }
            with open(self.config_file, 'w', encoding='utf-8') as f: json.dump(self.config, f, indent=2)
        except: pass

    def on_closing(self):
        self.save_config()
        self.root.destroy()

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
        if pyi_splash.is_alive(): pyi_splash.close()
    except NameError: pass
    root.mainloop()
'''

def localize_code(code_str, lang):
    """
    EN版作成時に、JP版コード内の日本語を英語に置換する関数
    """
    if lang == "JP":
        return code_str
    
    print("  ...日本語UIを英語に変換中...")
    
    replacements = {
        # タイトル・基本
        f'v{VERSION.replace("v","")} JP': f'v{VERSION.replace("v","")} EN',
        'text="🗣️ TTS (音声合成)"': 'text="🗣️ TTS (Voice Synthesis)"',
        
        # サーバー状態
        'text="サーバー・エンジン状態"': 'text="Server/Engine Status"',
        'text="Coqui TTS: 起動処理中..."': 'text="Coqui TTS: Initializing..."',
        'text="VOICEVOX: 確認中..."': 'text="VOICEVOX: Checking..."',
        'text="🔄 再接続"': 'text="🔄 Reconnect"',
        'text="＊再接続のためVOICEVOXを起動してください"': 'text="*Launch VOICEVOX to reconnect"',
        
        # エンジン選択
        'text="🎙️ 音声生成エンジン選択"': 'text="🎙️ Select Generation Engine"',
        'text="Coqui TTS XTTS (ファイル参照型)"': 'text="Coqui TTS XTTS (Reference File)"',
        'text="VOICEVOX (内蔵キャラ型)"': 'text="VOICEVOX (Built-in Character)"',
        
        # 話者設定
        'text="👤 話者設定"': 'text="👤 Speaker Settings"',
        'text="話者ファイル:"': 'text="Ref Audio:"',
        'text="音声フォルダ"': 'text="Audio Folder"',
        'text="再適用"': 'text="Refresh"',
        'text="言語:"': 'text="Lang:"',
        'text="キャラクター:"': 'text="Character:"',
        
        # パラメータ
        'text="🎚️ 音声パラメータ設定 ([VV]: VOICEVOXのみ有効)"': 'text="🎚️ Audio Params ([VV]: VOICEVOX only)"',
        'text="話速:"': 'text="Speed:"',
        'text="音量:"': 'text="Volume:"',
        'text="音程 [VV]:"': 'text="Pitch [VV]:"',
        'text="抑揚 [VV]:"': 'text="Intonation [VV]:"',
        'text="🔇 無音設定 (秒)"': 'text="🔇 Silence Settings (sec)"',
        'text="開始:"': 'text="Start:"',
        'text="終了:"': 'text="End:"',
        'text="句読点:"': 'text="Punctuation:"',
        
        # テキスト入力
        'text="📝 テキスト入力"': 'text="📝 Text Input"',
        'text="📂 読込"': 'text="📂 Load"',
        'text="🗑️ 消去"': 'text="🗑️ Clear"',
        
        # 出力設定
        'text="💾 出力設定"': 'text="💾 Output Settings"',
        'text="出力先:"': 'text="Output Dir:"',
        'text="参照"': 'text="Browse"',
        'text="開く"': 'text="Open"',
        'text="形式:"': 'text="Format:"',
        'text="接頭辞:"': 'text="Prefix:"',
        'text="連番桁:"': 'text="Digits:"',
        'text="命名規則:"': 'text="Naming Rule:"',
        'text="タグ挿入:"': 'text="Insert Tags:"',
        'text="+文字(7)"': 'text="+Text(7)"',
        'text="+ID"': 'text="+ID"',
        'text="+日時"': 'text="+Date"',
        'text="+接頭辞"': 'text="+Prefix"',
        'text="+連番"': 'text="+Seq"',
        
        # ボタン
        'text="🎵 音声生成開始"': 'text="🎵 Generate Voice"',
        'text="⏹️ 生成停止"': 'text="⏹️ Stop Generation"',
        'text="🔄 設定リセット"': 'text="🔄 Reset Settings"',
        
        # ステータス・メッセージ
        'text="準備完了"': 'text="Ready"',
        'text="Coqui TTS: 準備完了"': 'text="Coqui TTS: Ready"',
        'text="Coqui TTS: 起動失敗"': 'text="Coqui TTS: Failed"',
        'text="VOICEVOX: 接続OK"': 'text="VOICEVOX: Connected"',
        'text="VOICEVOX: 未接続"': 'text="VOICEVOX: Disconnected"',
        '"成功", "VOICEVOXエンジンと接続しました！"': '"Success", "Connected to VOICEVOX!"',
        '"起動エラー", f"初期化中にエラーが発生しました': '"Init Error", f"Error during initialization',
        '"AIエンジン起動エラー", f"Coqui TTSの起動に失敗しました': '"Engine Error", f"Failed to start Coqui TTS',
        '"確認", "消去しますか？"': '"Confirm", "Clear all text?"',
        '"Coqui TTS起動中です。"': '"Coqui TTS is starting up."',
        'text="🎵 生成中..."': 'text="🎵 Generating..."',
        'text="⏹️ 停止処理中..."': 'text="⏹️ Stopping..."',
        'title("生成中")': 'title("Generating")',
        'text="音声を生成しています..."': 'text="Generating voice..."',
        'f"生成中: {c}/{len(segments)}"': 'f"Processing: {c}/{len(segments)}"',
        '"完了！"': '"Done!"',
        'f"生成完了: {count}/{total}ファイル': 'f"Completed: {count}/{total} files',
        'text="設定をリセットしました"': 'text="Settings reset."',
    }
    
    for jp, en in replacements.items():
        code_str = code_str.replace(jp, en)
        
    return code_str

def create_edition(lang):
    """指定された言語(JP/EN)のパッケージを作成"""
    is_jp = (lang == "JP")
    suffix = "JP" if is_jp else "EN"
    app_filename = f"rogoai_voice_studio_{VERSION}_{suffix}_Slim.py"
    
    folder_name = f"{BASE_NAME}_{VERSION}_{suffix}"
    target_dir = os.path.join(DIST_ROOT, folder_name)
    
    print(f"\n>>> [{suffix}版] パッケージ作成開始: {folder_name}")
    
    # 1. フォルダ作成
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir)
    
    # 2. アプリファイル書き込み (★ここでEN版のみ英語置換を実行)
    final_code = localize_code(APP_SCRIPT_CONTENT, lang)
    
    with open(os.path.join(target_dir, app_filename), 'w', encoding='utf-8') as f:
        f.write(final_code)
    print(f"  アプリ本体: {app_filename} (v1.9.2)")

    # 3. アイコン (あれば)
    if os.path.exists("make_icon"):
        shutil.copytree("make_icon", os.path.join(target_dir, "make_icon"))

    # FFmpeg (あればコピー)
    if os.path.exists("ffmpeg"):
        print(f"  FFmpegを同梱中...")
        shutil.copytree("ffmpeg", os.path.join(target_dir, "ffmpeg"))

    # 4. requirements.txt 作成
    with open(os.path.join(target_dir, "requirements.txt"), 'w', encoding='utf-8') as f:
        f.write(REQUIREMENTS_CONTENT)

    # 5. バッチファイル作成
    if is_jp:
        # --- JP版バッチ ---
        
        # 1. Pythonインストール案内 (★修正済み: chcp 65001なし)
        with open(os.path.join(target_dir, "1_Pythonインストール(未導入の方のみ).bat"), 'w', encoding='cp932') as f:
            f.write(r"""@echo off
cls
echo ========================================
echo  RogoAI Voice Studio セットアップ
echo          ステップ 1 / 3
echo ========================================
echo.
echo 【確認】
echo   あなたのPCに Python 3.11 は入っていますか？
echo   入っていれば、このステップは不要です！
echo.
echo   次の「2_初回セットアップ」に進んでください。
echo.
echo ----------------------------------------
echo.
echo 【Python 3.11 が全くない場合】
echo.
echo   以下の手順でインストールしてください：
echo.
echo   1. 自動でダウンロードページが開きます
echo.
echo   2. 一番下までスクロールして
echo      「Windows installer (64-bit)」をクリック
echo.
echo   3. ダウンロードしたファイルを実行
echo.
echo   4. 画面真ん中の「Install Now」をクリックするだけ！
echo      (チェックボックスなどはそのままでOKです)
echo.
echo   5. インストール完了まで待つ
echo.
echo ========================================
echo.
echo 準備ができたら何かキーを押してダウンロードページを開きます...
pause
start https://www.python.org/downloads/release/python-3119/
""")

        # 2. 環境構築 (venv)
        with open(os.path.join(target_dir, "2_初回セットアップ(環境構築).bat"), 'w', encoding='cp932') as f:
            f.write(r"""@echo off
cls
echo ========================================
echo  RogoAI Voice Studio セットアップ
echo          ステップ 2 / 3
echo ========================================
echo.
echo 【これから行うこと】
echo.
echo   1. PC内の Python 3.11 を探します
echo   2. 専用環境(venv)を作成します
echo   3. 必要なライブラリを「安全な順序」で入れます
echo.
echo   ※所要時間：20-30分
echo.
pause
echo.

echo [1/5] Python 3.11 を検索中...
echo.

REM pyランチャー優先
py -3.11 --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [発見] pyランチャー経由で Python 3.11 を見つけました。
    set PYTHON_CMD=py -3.11
    goto create_venv
)

REM pythonコマンド確認
python --version 2>&1 | find "3.11" >nul
if %errorlevel% equ 0 (
    echo [発見] 標準の python コマンドが 3.11 です。
    set PYTHON_CMD=python
    goto create_venv
)

REM エラー
echo ========================================
echo  エラー: Python 3.11 が見つかりません
echo ========================================
echo.
echo 「1_Pythonインストール.bat」を実行して
echo Python 3.11 をインストールしてください。
echo.
pause
exit /b 1

:create_venv
echo.
echo [2/5] 専用環境(venv)を作成中...
echo.

if exist venv (
    rmdir /s /q venv
)

%PYTHON_CMD% -m venv venv

if %errorlevel% neq 0 (
    echo エラー: 環境の作成に失敗しました。
    pause
    exit /b 1
)

echo 環境作成完了！
echo.
echo [3/5] 基本ライブラリをインストール中 (pydub等)...
echo      ※ここが重要です。GUIの起動に必要なものを先に入れます。
echo.

REM pipアップデート
venv\Scripts\python -m pip install --upgrade pip

REM 重要: pydub, requests, Pillow を先にインストール
venv\Scripts\python -m pip install pydub requests Pillow

if %errorlevel% neq 0 (
    echo エラー: 基本ライブラリのインストールに失敗しました。
    pause
    exit /b 1
)

echo.
echo [4/5] PyTorch (GPU版) をインストール中...
echo      ※サイズが大きいので時間がかかります...
echo.

venv\Scripts\python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124

if %errorlevel% neq 0 (
    echo.
    echo  ※GPU版のインストールに失敗しました。CPU版を入れます。
    venv\Scripts\python -m pip install torch torchaudio
)

echo.
echo [5/5] 音声合成エンジン (TTS) をインストール中...
echo      ※これが一番時間がかかります (10-15分)
echo.

venv\Scripts\python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ----------------------------------------------------
    echo  [注意] TTSの一部のインストールに失敗した可能性があります。
    echo  ただし、基本機能は動作する可能性があります。
    echo  一度、起動を試してみてください。
    echo ----------------------------------------------------
    pause
)

echo.
echo ========================================
echo  セットアップ完了！
echo ========================================
echo.
echo 次からは「3_起動.bat」で起動できます。
pause
""")

        # 3. 起動
        with open(os.path.join(target_dir, "3_起動.bat"), 'w', encoding='cp932') as f:
            f.write(f"""@echo off
cd /d "%~dp0"
if not exist venv (
    echo エラー: セットアップが完了していません。
    echo 「2_初回セットアップ.bat」を実行してください。
    pause
    exit /b
)
start "" venv\Scripts\pythonw.exe {app_filename}
""")

        # 4. デバッグ起動
        with open(os.path.join(target_dir, "起動_デバッグ(黒画面).bat"), 'w', encoding='cp932') as f:
            f.write(f"""@echo off
cd /d "%~dp0"
if not exist venv (
    echo エラー: セットアップが完了していません。
    echo 「2_初回セットアップ.bat」を実行してください。
    pause
    exit /b
)
echo 起動中... エラーがあれば下に表示されます。
venv\Scripts\python.exe {app_filename}
pause
""")
            
        # README (JP)
        with open(os.path.join(target_dir, "README.txt"), 'w', encoding='utf-8-sig') as f:
            f.write(f"""========================================
 {BASE_NAME} {VERSION} ({suffix})
========================================

【使い方】

  1. 「1_Pythonインストール.bat」
     ※既に Python 3.11 が入っている方は【不要】です。

  2. 「2_初回セットアップ.bat」
     初回のみ実行します。
     ・PC内の Python 3.11 を自動で探して使います。
     ・このフォルダ内だけに専用環境を作ります。
     ・GPUがある場合はGPU版をインストールします。

  3. 「3_起動.bat」
     普段はこれをダブルクリックして起動します。

【トラブルシューティング】
  ・起動しない場合は「起動_デバッグ(黒画面).bat」を実行してください。
    エラーメッセージが表示されます。

  ・初回起動時はAIモデルのダウンロードに時間がかかります。

【開発者】
  Takejii (RogoAI)
========================================
""")

    else:
        # --- EN版バッチ (英語) ---
        
        # 1. Install Python (Simple)
        with open(os.path.join(target_dir, "1_Install_Python.bat"), 'w', encoding='ascii') as f:
            f.write("""@echo off
cls
echo ========================================
echo  RogoAI Voice Studio Setup
echo          STEP 1 / 3
echo ========================================
echo.
echo  [CHECK]
echo  Do you already have Python 3.11 installed?
echo  If YES, you can SKIP this step.
echo.
echo  Please proceed to "2_Setup_Environment".
echo.
echo ----------------------------------------
echo.
echo  [If you DON'T have Python 3.11]
echo.
echo  1. The download page will open automatically
echo.
echo  2. Scroll down and click "Windows installer (64-bit)"
echo.
echo  3. Run the installer
echo.
echo  4. Just click "Install Now" (No need to check boxes)
echo.
echo ========================================
pause
start https://www.python.org/downloads/release/python-3119/
""")

        # 2. Setup Env (Ordered)
        with open(os.path.join(target_dir, "2_Setup_Environment.bat"), 'w', encoding='ascii') as f:
            f.write("""@echo off
cls
echo ========================================
echo  RogoAI Voice Studio Setup
echo          STEP 2 / 3
echo ========================================
echo.
echo  1. Searching for Python 3.11 on your PC...
echo  2. Creating dedicated environment (venv)...
echo  3. Installing libraries in SAFE ORDER...
echo.
echo   *Estimated time: 20-30 mins
echo.
pause
echo.

echo [1/5] Searching for Python 3.11...
echo.

REM Method 1: py launcher
py -3.11 --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [Found] Python 3.11 via py launcher.
    set PYTHON_CMD=py -3.11
    goto create_venv
)

REM Method 2: python command
python --version 2>&1 | find "3.11" >nul
if %errorlevel% equ 0 (
    echo [Found] Default python command is 3.11.
    set PYTHON_CMD=python
    goto create_venv
)

echo ========================================
echo  ERROR: Python 3.11 not found
echo ========================================
echo.
echo Please run "1_Install_Python.bat".
echo.
pause
exit /b 1

:create_venv
echo.
echo [2/5] Creating venv...
echo.

if exist venv (
    rmdir /s /q venv
)

%PYTHON_CMD% -m venv venv

if %errorlevel% neq 0 (
    echo ERROR: Failed to create environment.
    pause
    exit /b 1
)

echo.
echo [3/5] Installing Basic Libraries (pydub, requests...)...
echo.

venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install pydub requests Pillow

if %errorlevel% neq 0 (
    echo ERROR: Failed to install basic libraries.
    pause
    exit /b 1
)

echo.
echo [4/5] Installing PyTorch (GPU version)...
echo.

venv\Scripts\python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124

if %errorlevel% neq 0 (
    echo.
    echo  *GPU install failed. Trying CPU version...
    venv\Scripts\python -m pip install torch torchaudio
)

echo.
echo [5/5] Installing TTS Engine...
echo      (This takes time...)
echo.

venv\Scripts\python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ----------------------------------------------------
    echo  WARNING: TTS installation had issues.
    echo  However, the app might still work.
    echo  Please try launching it.
    echo ----------------------------------------------------
    pause
)

echo.
echo ========================================
echo  Setup Complete!
echo ========================================
echo.
echo You can now run "3_Start.bat".
pause
""")

        # 3. Start
        with open(os.path.join(target_dir, "3_Start.bat"), 'w', encoding='ascii') as f:
            f.write(f'@echo off\ncd /d "%~dp0"\nif not exist venv (\n  echo Please run 2_Setup_Environment.bat first.\n  pause\n  exit /b\n)\nstart "" venv\Scripts\pythonw.exe {app_filename}\n')

        # 4. Debug Start
        with open(os.path.join(target_dir, "Start_Debug.bat"), 'w', encoding='ascii') as f:
            f.write(f'@echo off\ncd /d "%~dp0"\nif not exist venv (\n  echo Please run 2_Setup_Environment.bat first.\n  pause\n  exit /b\n)\necho Launching...\nvenv\Scripts\python.exe {app_filename}\npause\n')

        # README (EN)
        with open(os.path.join(target_dir, "README.txt"), 'w', encoding='utf-8') as f:
            f.write(f"""========================================
 {BASE_NAME} {VERSION} ({suffix})
========================================

[INSTRUCTIONS]

  1. Run "1_Install_Python.bat"
     (Only if you don't have Python 3.11 installed)

  2. Run "2_Setup_Environment.bat"
     (Run once. Takes 20-30 mins)
     *Automatically finds Python 3.11.
     *Creates a dedicated environment here.

  3. Run "3_Start.bat"
     (Double-click to launch app)

[TROUBLESHOOTING]
  - If app doesn't start, run "Start_Debug.bat" to see errors.
  - First launch takes time to download AI models.

[DEVELOPER]
  Takejii (RogoAI)
========================================
""")

    print(f"  ✅ {suffix}版 作成完了")
    return target_dir

def main():
    print("="*60)
    print(f"  {BASE_NAME} 配布パッケージ作成ツール (v1.9.2: GUI修正版)")
    print("="*60)

    # 1. JP版の作成
    create_edition("JP")

    # 2. EN版の作成
    create_edition("EN")
    
    print("\n" + "="*60)
    print("  🎉 全工程完了！ distフォルダを確認してください")
    print("="*60)

if __name__ == "__main__":
    main()