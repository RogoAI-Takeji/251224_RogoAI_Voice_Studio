
"""
ROGOAI Voice Studio v2.4 JP
Universal Voice Generation Platform

機能:
1. VOICEVOXキャラクター音声生成
2. Coqui TTS XTTS Zero-Shot Voice Cloning
3. GUI刷新: スリム化＆カスタムファイル名命名機能
4. 安全な非同期起動処理
5. JP/EN展開を見据えたUI調整
★6. Daily Logger: 音声生成時のテキスト自動記録機能
★7. Whisper音声認識: faster-whisperによる高速文字起こし
   - base (精度85%) / medium (精度95%) / large-v3 (精度98%) モデル選択
   - テキスト/SRT字幕形式出力
   - 音声生成タブへの転送機能
★8. プリセット管理: よく使う設定を保存・呼び出し
★9. 音声プレビュー: 最初の30文字だけ生成してテスト
★10. バッチ処理: 複数ファイルの一括処理
★11. テキスト履歴: 最近使った10件を保存
★12. テンプレート機能: 定型文の保存・呼び出し
★13. 自動バックアップ: テキスト入力中に自動保存
★14. サウンドレコーダー: マイクから直接録音→文字起こし
★★★ v2.4 新機能 ★★★
★15. 複数ファイル文字起こし: 複数音声ファイルを一括処理（1行空けて統合保存）
★16. 自動保存: タイムスタンプ+内容先頭20文字でファイル名自動生成
★17. TreeViewフォルダブラウザ: Explorerライクな使いやすいフォルダ選択
     - フォルダとファイルを同時表示
     - デスクトップへワンクリック移動
     - 新規フォルダ作成機能
★18. ワークフロー改善: 録音→文字起こしが18ステップ→5ステップに短縮（72%削減）
★19. UI簡素化: 不要なボタン削除、操作性向上

Author: ROGOAI
Version: 2.4 JP (Multi-File Transcription & TreeView Browser Edition)
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

# 録音機能用 (v2.3で追加)
try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    RECORDING_AVAILABLE = True
except ImportError:
    RECORDING_AVAILABLE = False
    print("⚠ 録音機能が無効です: sounddevice または soundfile がインストールされていません")

# ==========================================
# exe化対応：could not get source code エラー回避パッチ
# ==========================================
import inspect
import sys

# exe化されている場合、ソースコード取得でエラーが出ないように空文字を返す
if getattr(sys, 'frozen', False):
    def _safe_getsource(object):
        return ""
    inspect.getsource = _safe_getsource
# ==========================================


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
# Whisper音声認識 (v2.1で追加)
try:
    from whisper_engine import WhisperEngine
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("⚠️ Warning: whisper_engine.py not found. Whisper機能は無効化されます。")


CUDA_AVAILABLE = torch.cuda.is_available()
CUDA_DEVICE = torch.cuda.get_device_name(0) if CUDA_AVAILABLE else "CPU"
# ==========================================

# ==========================================
# exe化対応：リソースパス取得関数
# ==========================================
def resource_path(relative_path):
    """exe化された環境(_MEIPASS)でも正しくパスを取得する"""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path



def setup_ffmpeg():
    # 修正前: base_path = Path(__file__).parent
    # 修正後:
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
        self.root.title(f"🎙️ ROGOAI Voice Studio v2.4 JP - {gpu_status}")

        try:
            # 修正前: icon_path = Path(__file__).parent / "make_icon" / "icon.ico"
            # 修正後:
            icon_path = resource_path("make_icon/icon.ico")
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except:
            pass
        
        self.root.geometry("800x920")
        
        self.app_data = self.get_app_data_path()
        self.voicevox_server_url = "http://127.0.0.1:50021"
        
        self.coqui_enabled = False
        self.coqui_model = None
        self.samples_dir = self.app_data / "samples"
        self.samples_dir.mkdir(parents=True, exist_ok=True)
        
        self.generation_stop_flag = False
        self.config_file = self.app_data / "config.json"
        
        # Whisper音声認識エンジン (v2.1で追加)
        self.whisper_engine = None
        self.whisper_model_var = tk.StringVar(value='base')
        self.whisper_language_var = tk.StringVar(value='ja')
        self.whisper_format_var = tk.StringVar(value='text')
        
        # 録音機能 (v2.3で追加)
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
        self.load_config()  # 先にconfigを読み込む
        
        # v2.2 新機能用変数 (configを読み込んだ後に初期化)
        self.presets = self.config.get('presets', {})
        self.current_preset = tk.StringVar(value='デフォルト')
        self.text_history = self.config.get('text_history', [])
        self.templates = self.config.get('templates', {})
        self.auto_backup_enabled = True
        self.backup_timer_id = None
        
        # v2.3 録音完了メッセージの表示設定
        self.show_recording_complete_message = self.config.get('show_recording_complete_message', True)
        
        self.voicevox_speakers = []
        self.build_gui()
        self.initialize_app_async()
        
        # v2.2 デフォルトプリセットを自動作成（初回起動時のみ）
        if 'デフォルト' not in self.presets:
            # 初期設定を「デフォルト」として保存
            self.presets['デフォルト'] = {
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
        
        # v2.2 自動バックアップ開始
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
        (app_path / 'logs').mkdir(exist_ok=True)  # Daily Logger用
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
        
        # Tab 1: 音声認識 (Whisper) - STT → TTS の流れを考慮して最初に配置
        if WHISPER_AVAILABLE:
            self.tab_stt = ttk.Frame(self.notebook)
            self.notebook.add(self.tab_stt, text="🎤 STT (音声認識)")
            self.build_stt_tab(self.tab_stt)
        
        # Tab 2: 音声合成 (TTS)
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
        
        # v2.2 プリセット管理UI
        self.build_preset_ui(main_frame)

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
        
        # プレビューボタン（パラメーター調整時に使いやすい位置）
        ttk.Label(silence_frame, text="").pack(side=tk.LEFT, padx=10)  # スペーサー
        ttk.Button(silence_frame, text="🔊 プレビュー（30文字）", 
                  command=self.preview_voice, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(silence_frame, text="❓", 
                  command=self.show_preview_help, width=3).pack(side=tk.LEFT, padx=1)


        # 5. テキスト入力
        text_frame = ttk.LabelFrame(main_frame, text="📝 テキスト入力", padding="2")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        tool_frame = ttk.Frame(text_frame)
        tool_frame.pack(fill=tk.X)
        
        ttk.Button(tool_frame, text="📂 ファイル読込", command=self.load_text_file, width=12).pack(side=tk.LEFT)
        tk.Button(tool_frame, text="🗑️ 消去", command=self.clear_text_input, bg="#dc3545", fg="white", font=("", 8, "bold"), relief=tk.RAISED, width=8).pack(side=tk.LEFT, padx=10)
        ttk.Button(tool_frame, text="📄 変換log.txt", command=self.open_output_dir, width=14).pack(side=tk.LEFT, padx=5)
        
        self.text_input = scrolledtext.ScrolledText(text_frame, width=60, height=5)
        self.text_input.pack(fill=tk.BOTH, expand=True)

        # 6. 出力設定
        output_frame = ttk.LabelFrame(main_frame, text="💾 出力設定", padding="5")
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(output_frame, text="出力先:").grid(row=0, column=0, sticky=tk.W, padx=5)
        default_output = self.config.get('output_dir', str(self.app_data / 'outputs'))
        self.output_dir_var = tk.StringVar(value=default_output)
        ttk.Entry(output_frame, textvariable=self.output_dir_var, width=28).grid(row=0, column=1, padx=5, columnspan=2, sticky=tk.W+tk.E)
        
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

        
        
        # v2.2 拡張機能ボタン
        advanced_frame = ttk.Frame(main_frame)
        advanced_frame.pack(fill=tk.X, pady=3)
        
        ttk.Button(advanced_frame, text="📂 フォルダ一括読み込み", command=self.batch_generate, width=20).pack(side=tk.LEFT, padx=3)
        ttk.Button(advanced_frame, text="📝 テンプレート", command=self.load_template, width=15).pack(side=tk.LEFT, padx=3)
        ttk.Button(advanced_frame, text="💾", command=self.save_template, width=3).pack(side=tk.LEFT, padx=1)
        ttk.Button(advanced_frame, text="❓", command=self.show_template_help, width=3).pack(side=tk.LEFT, padx=1)
        ttk.Button(advanced_frame, text="📋 履歴", command=self.show_text_history, width=10).pack(side=tk.LEFT, padx=3)


        # 7. ボタン群
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        self.generate_button = tk.Button(button_frame, text="🎵 音声生成開始", command=self.generate_voice, bg="#28a745", fg="white", font=("", 12, "bold"), padx=15, pady=5, relief=tk.RAISED, cursor="hand2")
        self.generate_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = tk.Button(button_frame, text="⏹️ 生成停止", command=self.stop_generation, bg="#dc3545", fg="white", font=("", 12, "bold"), padx=15, pady=5, relief=tk.RAISED, cursor="hand2", state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔔 ポップアップを復活", command=self.restore_popups).pack(side=tk.LEFT, padx=5)
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
        # Windowsで無効な文字を除去
        invalid_chars = [':', '*', '?', '"', '<', '>', '|', '/', '\\']
        clean_text = text.replace('\n', '').replace('\r', '').replace(' ', '').replace('　', '')
        for char in invalid_chars:
            clean_text = clean_text.replace(char, '')
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
    
    def restore_popups(self):
        """すべてのポップアップ通知を復活させる"""
        # 現在「今後表示しない」が選択されているポップアップを確認
        disabled_popups = []
        
        if not self.show_recording_complete_message:
            disabled_popups.append("録音完了通知")
        
        if not self.config.get('show_generation_complete', True):
            disabled_popups.append("音声生成完了通知")
        
        if not self.config.get('show_transcription_complete', True):
            disabled_popups.append("文字起こし完了通知")
        
        # 無効化されているポップアップがない場合
        if not disabled_popups:
            messagebox.showinfo(
                "ポップアップ復活",
                "すべてのポップアップ通知は既に有効です。\n\n"
                "無効化されている通知はありません。"
            )
            return
        
        # 復活確認
        popup_list = "\n・".join(disabled_popups)
        result = messagebox.askyesno(
            "ポップアップ復活",
            f"以下のポップアップ通知を復活させますか？\n\n"
            f"・{popup_list}\n\n"
            f"これらの通知が再度表示されるようになります。"
        )
        
        if result:
            # すべてのポップアップを復活
            self.show_recording_complete_message = True
            self.config['show_recording_complete_message'] = True
            self.config['show_generation_complete'] = True
            self.config['show_transcription_complete'] = True
            self.save_config()
            
            messagebox.showinfo(
                "完了",
                "すべてのポップアップ通知を復活させました。\n\n"
                "次回から通知が表示されます。"
            )
            self.status_bar.config(text="✅ ポップアップ通知を復活しました")
        else:
            self.status_bar.config(text="ポップアップ復活をキャンセルしました")

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
                self.write_daily_log(fname, seg, output_dir)  # Daily Logger記録
                count += 1
            
            self.root.after(0, lambda: self._update_progress(100, "完了！"))
            self.root.after(0, lambda: self._on_generation_complete(count, len(segments), output_dir))
        except Exception as e:
            traceback.print_exc()
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("エラー", msg))
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
        """音声生成完了通知（チェックボックス付き）"""
        # 設定で非表示になっている場合はスキップ
        if not self.config.get('show_generation_complete', True):
            return
        
        # チェックボックス付きダイアログを表示
        dialog = tk.Toplevel(self.root)
        dialog.title("完了")
        dialog.geometry("450x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # タイトル
        ttk.Label(dialog, text="✅ 音声生成完了", 
                 font=("", 12, "bold")).pack(pady=10)
        
        # 完了メッセージ
        msg_frame = ttk.Frame(dialog)
        msg_frame.pack(pady=10)
        
        ttk.Label(msg_frame, text=f"生成ファイル数: {count}/{total}").pack()
        ttk.Label(msg_frame, text=f"保存先: {output_dir}").pack()
        ttk.Label(msg_frame, text="※音声ファイルとログ(YYYYMMDD_log.txt)を保存しました", 
                 font=("", 8), foreground="gray").pack()
        
        # チェックボックス
        dont_show_var = tk.BooleanVar()
        check_frame = ttk.Frame(dialog)
        check_frame.pack(pady=15)
        
        ttk.Checkbutton(check_frame, text="今後この通知を表示しない", 
                       variable=dont_show_var).pack()
        
        # 設定復活方法の案内
        info_label = ttk.Label(dialog, 
                              text="※設定の復活: TTSタブの「ポップアップを復活」ボタン",
                              font=("", 8), foreground="blue")
        info_label.pack(pady=5)
        
        # OKボタン
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
        d = self.browse_folder_with_file_preview(
            title="出力先フォルダを選択",
            initialdir=self.output_dir_var.get()
        )
        if d: self.output_dir_var.set(d)
    
    def browse_folder_with_file_preview(self, title="フォルダを選択", initialdir=None):
        """
        TreeViewを使ったExplorerライクなフォルダ選択ダイアログ
        ファイルとフォルダを両方表示し、フォルダのみ選択可能
        """
        class FolderBrowserDialog:
            def __init__(self, parent, title, initialdir):
                self.result = None
                self.dialog = tk.Toplevel(parent)
                self.dialog.title(title)
                self.dialog.geometry("700x500")
                self.dialog.transient(parent)
                self.dialog.grab_set()
                
                # 初期ディレクトリ
                if initialdir and Path(initialdir).exists():
                    self.current_path = Path(initialdir)
                else:
                    self.current_path = Path.home()
                
                self._build_ui()
                self._populate_tree()
                
                # ダイアログを中央に配置
                self.dialog.update_idletasks()
                x = (parent.winfo_screenwidth() // 2) - (700 // 2)
                y = (parent.winfo_screenheight() // 2) - (500 // 2)
                self.dialog.geometry(f"+{x}+{y}")
            
            def _build_ui(self):
                """UIを構築"""
                # 上部: パス表示
                path_frame = ttk.Frame(self.dialog)
                path_frame.pack(fill=tk.X, padx=10, pady=5)
                
                ttk.Label(path_frame, text="選択中:").pack(side=tk.LEFT)
                self.path_var = tk.StringVar(value=str(self.current_path))
                ttk.Entry(path_frame, textvariable=self.path_var, 
                         state='readonly').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
                
                # ナビゲーションボタン
                ttk.Button(path_frame, text="↑", width=3,
                          command=self._go_parent).pack(side=tk.LEFT, padx=2)
                ttk.Button(path_frame, text="デスクトップ", width=10,
                          command=self._go_desktop).pack(side=tk.LEFT, padx=2)
                ttk.Button(path_frame, text="📁 新規", width=6,
                          command=self._create_folder).pack(side=tk.LEFT, padx=2)
                
                # 中央: TreeView
                tree_frame = ttk.Frame(self.dialog)
                tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
                
                # スクロールバー
                scrollbar = ttk.Scrollbar(tree_frame)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                # TreeView
                self.tree = ttk.Treeview(tree_frame, yscrollcommand=scrollbar.set,
                                        selectmode='browse')
                self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.config(command=self.tree.yview)
                
                # 列設定
                self.tree['columns'] = ('type', 'size')
                self.tree.column('#0', width=400, minwidth=200)
                self.tree.column('type', width=100, minwidth=80)
                self.tree.column('size', width=100, minwidth=80)
                
                self.tree.heading('#0', text='名前')
                self.tree.heading('type', text='種類')
                self.tree.heading('size', text='サイズ')
                
                # イベント
                self.tree.bind('<Double-Button-1>', self._on_double_click)
                self.tree.bind('<<TreeviewSelect>>', self._on_select)
                
                # 下部: ボタン
                button_frame = ttk.Frame(self.dialog)
                button_frame.pack(fill=tk.X, padx=10, pady=10)
                
                ttk.Button(button_frame, text="OK", width=10,
                          command=self._on_ok).pack(side=tk.RIGHT, padx=5)
                ttk.Button(button_frame, text="キャンセル", width=10,
                          command=self._on_cancel).pack(side=tk.RIGHT, padx=5)
                
                # ヘルプ
                ttk.Label(button_frame, 
                         text="💡 フォルダをダブルクリックで開く、選択してOKで確定",
                         foreground="blue", font=("", 9)).pack(side=tk.LEFT)
            
            def _populate_tree(self):
                """TreeViewにファイル・フォルダを表示"""
                # ツリーをクリア
                for item in self.tree.get_children():
                    self.tree.delete(item)
                
                try:
                    items = list(self.current_path.iterdir())
                    
                    # フォルダとファイルに分類
                    folders = sorted([x for x in items if x.is_dir()], 
                                   key=lambda x: x.name.lower())
                    files = sorted([x for x in items if x.is_file()], 
                                 key=lambda x: x.name.lower())
                    
                    # フォルダを追加
                    for folder in folders:
                        try:
                            self.tree.insert('', 'end', 
                                           text=f"📁 {folder.name}",
                                           values=('フォルダ', ''),
                                           tags=('folder',))
                        except:
                            pass
                    
                    # ファイルを追加（グレーアウト）
                    for file in files:
                        try:
                            size = file.stat().st_size
                            size_str = self._format_size(size)
                            self.tree.insert('', 'end',
                                           text=f"📄 {file.name}",
                                           values=('ファイル', size_str),
                                           tags=('file',))
                        except:
                            pass
                    
                    # タグの色設定
                    self.tree.tag_configure('file', foreground='gray')
                    
                except PermissionError:
                    self.tree.insert('', 'end', text='⚠️ アクセス権限がありません')
                except Exception as e:
                    self.tree.insert('', 'end', text=f'⚠️ エラー: {str(e)}')
            
            def _format_size(self, size):
                """ファイルサイズをフォーマット"""
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024.0:
                        return f"{size:.1f} {unit}"
                    size /= 1024.0
                return f"{size:.1f} TB"
            
            def _on_double_click(self, event):
                """ダブルクリック時の処理"""
                selection = self.tree.selection()
                if not selection:
                    return
                
                item = selection[0]
                tags = self.tree.item(item, 'tags')
                
                # フォルダの場合は開く
                if 'folder' in tags:
                    item_text = self.tree.item(item, 'text')
                    folder_name = item_text.replace('📁 ', '')
                    new_path = self.current_path / folder_name
                    
                    if new_path.exists() and new_path.is_dir():
                        self.current_path = new_path
                        self.path_var.set(str(self.current_path))
                        self._populate_tree()
            
            def _on_select(self, event):
                """選択時の処理"""
                selection = self.tree.selection()
                if not selection:
                    return
                
                item = selection[0]
                tags = self.tree.item(item, 'tags')
                
                # フォルダの場合はパスを更新
                if 'folder' in tags:
                    item_text = self.tree.item(item, 'text')
                    folder_name = item_text.replace('📁 ', '')
                    selected_path = self.current_path / folder_name
                    self.path_var.set(str(selected_path))
                else:
                    # ファイルの場合は現在のパスを表示
                    self.path_var.set(str(self.current_path))
            
            def _go_parent(self):
                """親フォルダへ移動"""
                if self.current_path.parent != self.current_path:
                    self.current_path = self.current_path.parent
                    self.path_var.set(str(self.current_path))
                    self._populate_tree()
            
            def _go_desktop(self):
                """デスクトップへ移動"""
                self.current_path = Path.home() / "Desktop"
                if not self.current_path.exists():
                    self.current_path = Path.home()
                self.path_var.set(str(self.current_path))
                self._populate_tree()
            
            def _create_folder(self):
                """新規フォルダ作成"""
                from tkinter import simpledialog, messagebox
                
                folder_name = simpledialog.askstring(
                    "新規フォルダ",
                    "フォルダ名を入力してください:",
                    parent=self.dialog
                )
                
                if folder_name:
                    # 無効な文字をチェック
                    invalid_chars = '<>:"/\\|?*'
                    if any(c in folder_name for c in invalid_chars):
                        messagebox.showerror(
                            "エラー",
                            f"フォルダ名に使用できない文字が含まれています:\n{invalid_chars}"
                        )
                        return
                    
                    new_folder = self.current_path / folder_name
                    
                    if new_folder.exists():
                        messagebox.showwarning("警告", "同名のフォルダが既に存在します")
                        return
                    
                    try:
                        new_folder.mkdir(parents=True, exist_ok=True)
                        self._populate_tree()
                        messagebox.showinfo("成功", f"フォルダを作成しました:\n{folder_name}")
                    except Exception as e:
                        messagebox.showerror("エラー", f"フォルダの作成に失敗しました:\n{str(e)}")
            
            def _on_ok(self):
                """OKボタン"""
                # パス表示からフォルダパスを取得
                selected_path = Path(self.path_var.get())
                
                if selected_path.exists() and selected_path.is_dir():
                    self.result = str(selected_path)
                    self.dialog.destroy()
                else:
                    from tkinter import messagebox
                    messagebox.showwarning("警告", "有効なフォルダを選択してください")
            
            def _on_cancel(self):
                """キャンセルボタン"""
                self.result = None
                self.dialog.destroy()
        
        # ダイアログを表示
        browser = FolderBrowserDialog(self.root, title, initialdir)
        self.root.wait_window(browser.dialog)
        return browser.result

    def load_config(self):
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f: self.config = json.load(f)
        else: self.config = {}

    def save_config(self):
        try:
            # 既存のconfigを保持しつつ更新
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
        """Daily Logger: 音声生成時にテキストを日付別ログファイルに記録（出力先と同じフォルダ）"""
        try:
            today = datetime.now().strftime("%Y%m%d")
            log_file = output_dir / f"{today}_log.txt"
            clean_text = ' '.join(text.split())  # 改行・連続空白を単一スペースに
            with open(log_file, 'a', encoding='utf-8-sig') as f:
                f.write(f"{filename} : {clean_text}\n")
        except Exception as e:
            print(f"[Daily Logger] ログ書き込み失敗: {e}")

    def on_closing(self):
        self.save_config()
        self.root.destroy()


    
    # ==========================================
    # Whisper音声認識機能 (v2.1で追加)
    # ==========================================
    
    def build_stt_tab(self, parent):
        """音声認識(STT)タブのUI構築"""
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(title_frame, text="🎤 Whisper音声認識", 
                 font=("", 12, "bold")).pack(side=tk.LEFT)
        ttk.Label(title_frame, text="音声ファイルをテキストに変換", 
                 font=("", 9), foreground="gray").pack(side=tk.LEFT, padx=10)
        
        # 音声入力方法選択 (v2.3で追加)
        input_method_frame = ttk.LabelFrame(main_frame, text="🎙️ 音声入力方法", padding=10)
        input_method_frame.pack(fill=tk.X, pady=5)
        
        # ラジオボタン
        ttk.Radiobutton(input_method_frame, text="ファイルから選択", 
                       variable=self.audio_input_method_var, 
                       value='file',
                       command=self.toggle_audio_input_method).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(input_method_frame, text="マイクから録音", 
                       variable=self.audio_input_method_var, 
                       value='mic',
                       command=self.toggle_audio_input_method).pack(side=tk.LEFT, padx=10)
        
        # ファイル選択UI（v2.4で簡略化）
        self.file_select_frame = ttk.Frame(input_method_frame)
        self.file_select_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.file_select_frame, 
                 text="💡 「文字起こし開始」ボタンでファイル選択ダイアログが開きます（複数選択可）", 
                 foreground="blue", font=("", 9)).pack(side=tk.LEFT, padx=5)
        
        # 録音UI
        self.recording_frame = ttk.Frame(input_method_frame)
        # 初期状態では非表示
        
        # 録音保存先設定
        rec_output_frame = ttk.Frame(self.recording_frame)
        rec_output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(rec_output_frame, text="保存先:", width=10).pack(side=tk.LEFT)
        ttk.Entry(rec_output_frame, textvariable=self.recording_output_dir_var, 
                 width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(rec_output_frame, text="参照", 
                  command=self.browse_recording_output_dir, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(rec_output_frame, text="📁 開く", 
                  command=self.open_recording_output_dir, width=8).pack(side=tk.LEFT, padx=2)
        
        rec_buttons_frame = ttk.Frame(self.recording_frame)
        rec_buttons_frame.pack(fill=tk.X, pady=2)
        
        self.record_start_button = tk.Button(rec_buttons_frame, text="🔴 録音開始", 
                                            command=self.start_recording,
                                            bg="#dc3545", fg="white", 
                                            font=("", 10, "bold"), width=12)
        self.record_start_button.pack(side=tk.LEFT, padx=5)
        
        self.record_stop_button = tk.Button(rec_buttons_frame, text="⏹️ 停止",
                                           command=self.stop_recording,
                                           state='disabled', width=10)
        self.record_stop_button.pack(side=tk.LEFT, padx=5)
        
        # 録音時間表示
        self.recording_time_var = tk.StringVar(value="録音時間: 00:00:00")
        ttk.Label(rec_buttons_frame, textvariable=self.recording_time_var,
                 font=("", 10)).pack(side=tk.LEFT, padx=10)
        
        # 録音ファイル名表示
        self.recording_filename_var = tk.StringVar(value="")
        ttk.Label(self.recording_frame, textvariable=self.recording_filename_var,
                 foreground="gray", font=("", 8)).pack(fill=tk.X, pady=2)
        
        # v2.4 説明追加
        ttk.Label(self.recording_frame, 
                 text="💡 録音後、「文字起こし開始」ボタンで録音フォルダから選択できます（複数選択可）", 
                 foreground="blue", font=("", 9)).pack(fill=tk.X, pady=5)
        
        # 認識設定
        settings_frame = ttk.LabelFrame(main_frame, text="⚙️ 認識設定", padding=10)
        settings_frame.pack(fill=tk.X, pady=5)
        
        # モデル選択
        model_frame = ttk.Frame(settings_frame)
        model_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(model_frame, text="モデル:", width=10).pack(side=tk.LEFT)
        
        # モデルと精度の定義
        models = [
            ('base (精度85%)', 'base'),
            ('medium (精度95%)', 'medium'),
            ('large-v3 (精度98%)', 'large-v3')
        ]
        
        for text, value in models:
            ttk.Radiobutton(model_frame, text=text, 
                           variable=self.whisper_model_var, 
                           value=value).pack(side=tk.LEFT, padx=10)
        
        # 言語選択
        lang_frame = ttk.Frame(settings_frame)
        lang_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(lang_frame, text="言語:", width=10).pack(side=tk.LEFT)
        lang_combo = ttk.Combobox(lang_frame, textvariable=self.whisper_language_var,
                                  values=['ja - 日本語', 'en - English', 'zh - 中文', 
                                         'ko - 한국어', 'fr - Français', 'de - Deutsch',
                                         'es - Español', 'it - Italiano', 'pt - Português'],
                                  state='readonly', width=15)
        lang_combo.pack(side=tk.LEFT, padx=5)
        
        # 出力形式
        format_frame = ttk.Frame(settings_frame)
        format_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(format_frame, text="形式:", width=10).pack(side=tk.LEFT)
        ttk.Radiobutton(format_frame, text="テキスト", 
                       variable=self.whisper_format_var, 
                       value='text').pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="SRT字幕", 
                       variable=self.whisper_format_var, 
                       value='srt').pack(side=tk.LEFT, padx=5)
        
        # 実行ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.transcribe_button = tk.Button(button_frame, text="🎤 文字起こし開始", 
                                          command=self.start_transcription,
                                          bg="#28a745", fg="white", 
                                          font=("", 11, "bold"), height=2)
        self.transcribe_button.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.transcribe_stop_button = tk.Button(button_frame, text="⏹️ 停止",
                                               command=self.stop_transcription,
                                               state='disabled', width=10)
        self.transcribe_stop_button.pack(side=tk.LEFT, padx=5)
        
        # v2.4 新機能: 文字起こし結果の自動保存先
        auto_save_frame = ttk.Frame(main_frame)
        auto_save_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(auto_save_frame, text="文字起こし結果:", width=15).pack(side=tk.LEFT)
        default_stt_output = str(self.app_data / 'outputs')
        self.stt_output_dir_var = tk.StringVar(value=default_stt_output)
        ttk.Entry(auto_save_frame, textvariable=self.stt_output_dir_var, 
                 width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(auto_save_frame, text="参照", 
                  command=self.browse_stt_output_dir, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(auto_save_frame, text="📁 開く", 
                  command=self.open_stt_output_dir, width=8).pack(side=tk.LEFT, padx=2)
        
        # 認識結果表示
        result_frame = ttk.LabelFrame(main_frame, text="📝 認識結果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.transcription_result = scrolledtext.ScrolledText(result_frame, 
                                                              width=60, height=15,
                                                              font=("", 10))
        self.transcription_result.pack(fill=tk.BOTH, expand=True)
        
        # 結果操作ボタン
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(action_frame, text="→ 音声生成タブへ転送", 
                  command=self.transfer_to_generation, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="🗑️ クリア", 
                  command=lambda: self.transcription_result.delete('1.0', tk.END), 
                  width=10).pack(side=tk.LEFT, padx=5)
    
    # ==========================================
    # v2.3 録音機能
    # ==========================================
    
    def toggle_audio_input_method(self):
        """音声入力方法の切り替え"""
        method = self.audio_input_method_var.get()
        
        if method == 'file':
            # ファイル選択UIを表示
            self.file_select_frame.pack(fill=tk.X, pady=5)
            self.recording_frame.pack_forget()
        else:  # mic
            # 録音UIを表示
            self.file_select_frame.pack_forget()
            self.recording_frame.pack(fill=tk.X, pady=5)
            
            if not RECORDING_AVAILABLE:
                messagebox.showerror(
                    "エラー",
                    "録音機能が利用できません。\n\n"
                    "sounddevice と soundfile をインストールしてください:\n"
                    "pip install sounddevice soundfile"
                )
                self.audio_input_method_var.set('file')
                self.toggle_audio_input_method()
    
    def start_recording(self):
        """録音開始"""
        if not RECORDING_AVAILABLE:
            messagebox.showerror("エラー", "録音機能が利用できません")
            return
        
        try:
            # 保存先フォルダを取得
            output_dir = Path(self.recording_output_dir_var.get())
            if not output_dir.exists():
                output_dir.mkdir(parents=True, exist_ok=True)
            
            # 録音ファイル名を生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"record_{timestamp}.wav"
            self.current_recording_file = output_dir / filename
            
            # 録音開始
            self.is_recording = True
            self.recording_data = []
            self.recording_start_time = time.time()
            
            # UIの状態変更
            self.record_start_button.config(state='disabled')
            self.record_stop_button.config(state='normal')
            self.recording_filename_var.set(f"保存先: {filename}")
            
            # 録音ストリーム開始（16kHz モノラル - Whisperの推奨設定）
            self.recording_stream = sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype='float32',
                callback=self.recording_callback
            )
            self.recording_stream.start()
            
            # 録音時間の更新を開始
            self.update_recording_time()
            
            self.status_bar.config(text="🔴 録音中...")
            
        except Exception as e:
            messagebox.showerror("録音エラー", f"録音を開始できませんでした:\n{str(e)}")
            self.is_recording = False
            self.record_start_button.config(state='normal')
            self.record_stop_button.config(state='disabled')
    
    def stop_recording(self):
        """録音停止"""
        if not self.is_recording:
            return
        
        try:
            # 録音ストリーム停止
            if self.recording_stream:
                self.recording_stream.stop()
                self.recording_stream.close()
                self.recording_stream = None
            
            # 録音時間更新の停止
            if self.recording_timer_id:
                self.root.after_cancel(self.recording_timer_id)
                self.recording_timer_id = None
            
            # 録音データを保存
            if self.recording_data:
                audio_data = np.concatenate(self.recording_data, axis=0)
                sf.write(self.current_recording_file, audio_data, 16000)
                
                # v2.4: 録音完了（ファイル選択は「文字起こし開始」で行う）
                
                duration = time.time() - self.recording_start_time
                self.status_bar.config(text=f"✅ 録音完了: {duration:.1f}秒")
                
                # 録音完了メッセージ（「今後表示しない」オプション付き）
                if self.show_recording_complete_message:
                    self.show_recording_complete_dialog(self.current_recording_file.name)
            else:
                self.status_bar.config(text="⚠ 録音データがありません")
            
            # UIの状態をリセット
            self.is_recording = False
            self.recording_data = []
            self.record_start_button.config(state='normal')
            self.record_stop_button.config(state='disabled')
            self.recording_time_var.set("録音時間: 00:00:00")
            
        except Exception as e:
            messagebox.showerror("録音エラー", f"録音の保存に失敗しました:\n{str(e)}")
            self.is_recording = False
            self.record_start_button.config(state='normal')
            self.record_stop_button.config(state='disabled')
    
    def recording_callback(self, indata, frames, time_info, status):
        """録音データのコールバック"""
        if status:
            print(f"録音ステータス: {status}")
        
        if self.is_recording:
            # 録音データを追加
            self.recording_data.append(indata.copy())
    
    def update_recording_time(self):
        """録音時間の更新"""
        if not self.is_recording:
            return
        
        elapsed = time.time() - self.recording_start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        
        time_str = f"録音時間: {hours:02d}:{minutes:02d}:{seconds:02d}"
        self.recording_time_var.set(time_str)
        
        # 1秒後に再度更新
        self.recording_timer_id = self.root.after(1000, self.update_recording_time)
    
    def show_recording_complete_dialog(self, filename):
        """録音完了ダイアログ（「今後表示しない」オプション付き）"""
        # カスタムダイアログを作成
        dialog = tk.Toplevel(self.root)
        dialog.title("録音完了")
        dialog.geometry("450x300")  # サイズを拡大
        dialog.resizable(False, False)
        
        # ウィンドウを中央に配置
        dialog.transient(self.root)
        dialog.grab_set()
        
        # メインフレーム
        main_frame = ttk.Frame(dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # アイコンとメッセージ
        message_frame = ttk.Frame(main_frame)
        message_frame.pack(fill=tk.X, expand=False, pady=5)
        
        ttk.Label(message_frame, text="✅", font=("", 24)).pack(pady=3)
        ttk.Label(message_frame, text="録音完了", 
                 font=("", 12, "bold")).pack(pady=3)
        ttk.Label(message_frame, text=f"録音を保存しました:\n{filename}\n\n「文字起こし開始」ボタンを押してください。",
                 justify=tk.CENTER).pack(pady=3)
        
        # セパレーター
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 「今後表示しない」チェックボックス
        dont_show_var = tk.BooleanVar(value=False)
        check_frame = ttk.Frame(main_frame)
        check_frame.pack(fill=tk.X, pady=5)
        
        ttk.Checkbutton(check_frame, text="✓ 今後この通知を表示しない", 
                       variable=dont_show_var).pack(anchor=tk.W, padx=10)
        
        # OKボタン
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
        ok_button.focus_set()  # フォーカスを設定
        
        # Enterキーでも閉じる
        dialog.bind('<Return>', lambda e: on_ok())
        dialog.bind('<Escape>', lambda e: on_ok())
        
        # ×ボタンでも正しく処理
        dialog.protocol("WM_DELETE_WINDOW", on_ok)
    
    def start_transcription(self):
        """v2.4 文字起こし開始（複数ファイル対応）"""
        # ラジオボタンの状態をチェック
        input_method = self.audio_input_method_var.get()
        
        # ファイル選択ダイアログを表示
        if input_method == 'file':
            # 通常のファイル選択（デスクトップなど）
            file_paths = filedialog.askopenfilenames(
                title="音声ファイルを選択（複数選択可）",
                filetypes=[
                    ("音声ファイル", "*.mp3 *.wav *.m4a *.flac *.ogg *.mp4 *.mkv *.avi"),
                    ("すべてのファイル", "*.*")
                ]
            )
        else:  # mic
            # 録音フォルダから選択
            recording_dir = self.recording_output_dir_var.get()
            file_paths = filedialog.askopenfilenames(
                title="録音ファイルを選択（複数選択可）",
                initialdir=recording_dir,  # 録音フォルダを初期表示
                filetypes=[
                    ("音声ファイル", "*.mp3 *.wav *.m4a *.flac *.ogg"),
                    ("すべてのファイル", "*.*")
                ]
            )
        
        if not file_paths:
            return  # キャンセルされた
        
        # 選択されたファイルを保存
        self.selected_audio_files = file_paths
        
        # UIの状態変更
        self.transcribe_button.config(state='disabled')
        self.transcribe_stop_button.config(state='normal')
        self.transcription_result.delete('1.0', tk.END)
        
        # バックグラウンドで実行
        threading.Thread(target=self._transcribe_worker, daemon=True).start()
    
    def _transcribe_worker(self):
        """v2.4 文字起こし処理（複数ファイル対応・自動保存）"""
        try:
            from datetime import datetime
            
            # Whisperエンジン初期化
            if not self.whisper_engine or \
               self.whisper_engine.model_size != self.whisper_model_var.get():
                self.root.after(0, lambda: self.transcription_result.insert(
                    tk.END, "🔧 Whisperエンジンを初期化中...\n"))
                self.root.after(0, lambda: self.transcription_result.see(tk.END))
                
                self.whisper_engine = WhisperEngine(
                    model_size=self.whisper_model_var.get(),
                    device='auto'
                )
            
            # 設定取得
            language = self.whisper_language_var.get().split(' - ')[0]
            output_format = self.whisper_format_var.get()
            total_files = len(self.selected_audio_files)
            
            # 全結果を統合
            all_results = []
            success_count = 0
            failed_files = []
            
            # ファイルごとに処理
            for i, file_path in enumerate(self.selected_audio_files, 1):
                file_path = Path(file_path)
                
                # 進捗表示
                self.root.after(0, lambda i=i, t=total_files, n=file_path.name: 
                              self.transcription_result.insert(tk.END, f"\n[{i}/{t}] {n}\n"))
                self.root.after(0, lambda: self.transcription_result.see(tk.END))
                
                try:
                    # 進捗コールバック
                    def progress_callback(message):
                        self.root.after(0, lambda m=message: self.transcription_result.insert(tk.END, f"  {m}\n"))
                        self.root.after(0, lambda: self.transcription_result.see(tk.END))
                    
                    # 文字起こし実行
                    result = self.whisper_engine.transcribe(
                        file_path,
                        language=language,
                        output_format=output_format,
                        progress_callback=progress_callback
                    )
                    
                    all_results.append(result)
                    success_count += 1
                    
                    self.root.after(0, lambda: self.transcription_result.insert(tk.END, "✅ 完了\n"))
                    
                except Exception as e:
                    failed_files.append(f"{file_path.name}: {str(e)}")
                    self.root.after(0, lambda e=e: self.transcription_result.insert(
                        tk.END, f"❌ エラー: {str(e)}\n"))
            
            # 結果を統合（1行空けて連結）
            combined_result = "\n\n".join(all_results)
            
            # ファイル名生成（タイムスタンプ + 内容の先頭20文字）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 内容の先頭20文字を取得（ファイル名に使用可能な文字のみ）
            first_text = combined_result[:20].strip()
            # 無効な文字を除去（英数字、日本語、一部記号のみ）
            safe_text = ""
            for c in first_text:
                if c.isalnum():  # 英数字
                    safe_text += c
                elif c in (' ', '_', '-', 'ー'):  # 許可する記号
                    safe_text += c
                elif '\u3040' <= c <= '\u309F':  # ひらがな
                    safe_text += c
                elif '\u30A0' <= c <= '\u30FF':  # カタカナ
                    safe_text += c
                elif '\u4E00' <= c <= '\u9FFF':  # 漢字
                    safe_text += c
            safe_text = safe_text.replace(' ', '_')[:20]
            
            # 拡張子
            ext = "srt" if output_format == "srt" else "txt"
            
            # ファイル名
            if safe_text:
                filename = f"{timestamp}_{safe_text}.{ext}"
            else:
                filename = f"{timestamp}.{ext}"
            
            # 保存先
            output_dir = Path(self.stt_output_dir_var.get())
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / filename
            
            # 同名ファイルがある場合は連番
            counter = 1
            while output_file.exists():
                if safe_text:
                    filename = f"{timestamp}_{safe_text}_{counter}.{ext}"
                else:
                    filename = f"{timestamp}_{counter}.{ext}"
                output_file = output_dir / filename
                counter += 1
            
            # ファイルに保存
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(combined_result)
            
            # 結果表示
            self.root.after(0, lambda: self.transcription_result.insert(tk.END, "\n" + "="*60 + "\n"))
            self.root.after(0, lambda: self.transcription_result.insert(tk.END, "✅ 文字起こし完了\n"))
            self.root.after(0, lambda: self.transcription_result.insert(tk.END, "="*60 + "\n\n"))
            
            # サマリー
            summary = f"処理完了: {success_count}/{total_files} ファイル\n"
            if failed_files:
                summary += f"失敗: {len(failed_files)}件\n"
                for failed in failed_files:
                    summary += f"  - {failed}\n"
            summary += f"\n💾 保存先: {output_file}\n\n"
            
            self.root.after(0, lambda s=summary: self.transcription_result.insert(tk.END, s))
            self.root.after(0, lambda: self.transcription_result.insert(tk.END, "="*60 + "\n\n"))
            self.root.after(0, lambda: self.transcription_result.insert(tk.END, combined_result))
            self.root.after(0, lambda: self.transcription_result.see(tk.END))
            
            # 完了通知
            if self.config.get('show_transcription_complete', True):
                self.root.after(0, lambda: self._show_transcription_complete())
            
        except Exception as e:
            error_msg = f"エラー: {str(e)}"
            self.root.after(0, lambda msg=error_msg: self.transcription_result.insert(tk.END, f"\n❌ {msg}\n"))
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("エラー", msg))
        finally:
            self.root.after(0, lambda: self.transcribe_button.config(state='normal'))
            self.root.after(0, lambda: self.transcribe_stop_button.config(state='disabled'))
    
    def stop_transcription(self):
        """文字起こし停止 (現在は未実装)"""
        messagebox.showinfo("情報", "停止機能は次のバージョンで実装予定です")
    
    def _show_transcription_complete(self):
        """文字起こし完了ダイアログ (チェックボックス付き)"""
        dialog = tk.Toplevel(self.root)
        dialog.title("完了")
        dialog.geometry("450x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="✅ 文字起こし完了", 
                 font=("", 12, "bold")).pack(pady=10)
        
        ttk.Label(dialog, text="結果を音声生成タブで使用しますか?").pack(pady=10)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def on_yes():
            self.transfer_to_generation()
            dialog.destroy()
        
        def on_no():
            dialog.destroy()
        
        ttk.Button(button_frame, text="はい", command=on_yes, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="いいえ", command=on_no, width=10).pack(side=tk.LEFT, padx=5)
        
        # チェックボックス
        dont_show_var = tk.BooleanVar()
        ttk.Checkbutton(dialog, text="今後この通知を表示しない", 
                       variable=dont_show_var).pack(pady=10)
        
        # 設定復活方法の案内
        info_label = ttk.Label(dialog, 
                              text="※設定の復活: TTSタブの「ポップアップを復活」ボタン",
                              font=("", 8), foreground="blue")
        info_label.pack(pady=5)
        
        def on_close():
            if dont_show_var.get():
                self.config['show_transcription_complete'] = False
                self.save_config()
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_close)
    
    def transfer_to_generation(self):
        """認識結果を音声生成タブへ転送（SRT形式は自動クリーニング）"""
        # 結果を取得（ヘッダーを除く）
        full_result = self.transcription_result.get('1.0', tk.END)
        
        # "✅ 文字起こし完了"以降のテキストを取得
        if "✅ 文字起こし完了" in full_result:
            result = full_result.split("="*60)[-1].strip()
        else:
            result = full_result.strip()
        
        # SRT形式を検出してテキストのみを抽出
        if self._is_srt_format(result):
            result = self._extract_text_from_srt(result)
        
        if result:
            # TTSタブへ切り替え（タブ順序変更後は Tab 1）
            self.notebook.select(1)
            
            # テキスト入力エリアに転送
            self.text_input.delete('1.0', tk.END)
            self.text_input.insert('1.0', result)
            
            messagebox.showinfo("転送完了", "テキストを音声生成タブへ転送しました\n（SRT形式の場合は番号・タイムスタンプを自動除去）")
    
    def _is_srt_format(self, text):
        """SRT形式かどうかを判定"""
        lines = text.strip().split('\n')
        if len(lines) < 3:
            return False
        
        # 最初の行が数字で、2行目にタイムスタンプ（-->）があればSRT形式
        try:
            int(lines[0].strip())
            return '-->' in lines[1]
        except:
            return False
    
    def _extract_text_from_srt(self, srt_text):
        """SRT形式からテキスト部分のみを抽出（空行で区切る）"""
        lines = srt_text.strip().split('\n')
        text_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 数字行（字幕番号）をスキップ
            if line.isdigit():
                i += 1
                continue
            
            # タイムスタンプ行をスキップ
            if '-->' in line:
                i += 1
                continue
            
            # 空行をスキップ
            if not line:
                i += 1
                continue
            
            # それ以外はテキスト行として抽出
            text_lines.append(line)
            i += 1
        
        # テキスト行を空行（\n\n）で結合
        # → TTSで複数ファイルに分割される
        return '\n\n'.join(text_lines)
    
    def save_transcription_result(self):
        """認識結果を保存"""
        # 結果を取得（ヘッダーを除く）
        full_result = self.transcription_result.get('1.0', tk.END)
        
        # "✅ 文字起こし完了"以降のテキストを取得
        if "✅ 文字起こし完了" in full_result:
            result = full_result.split("="*60)[-1].strip()
        else:
            result = full_result.strip()
        
        if not result:
            messagebox.showwarning("警告", "保存する内容がありません")
            return
        
        # デフォルトの拡張子
        default_ext = ".txt" if self.whisper_format_var.get() == 'text' else ".srt"
        
        file_path = filedialog.asksaveasfilename(
            title="保存先を選択",
            defaultextension=default_ext,
            filetypes=[
                ("テキストファイル", "*.txt"),
                ("SRT字幕", "*.srt"),
                ("すべてのファイル", "*.*")
            ]
        )
        
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(result)
            messagebox.showinfo("保存完了", f"ファイルを保存しました:\n{file_path}")
    
    def open_stt_output_dir(self):
        """STT保存先フォルダを開く"""
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
        """STT保存先フォルダを選択"""
        current_dir = self.stt_output_dir_var.get()
        if not current_dir:
            current_dir = str(self.app_data / 'outputs')
        
        selected_dir = self.browse_folder_with_file_preview(
            title="STT保存先フォルダを選択",
            initialdir=current_dir
        )
        
        if selected_dir:
            self.stt_output_dir_var.set(selected_dir)
    
    def browse_recording_output_dir(self):
        """録音保存先フォルダを選択"""
        current_dir = self.recording_output_dir_var.get()
        if not current_dir:
            current_dir = str(self.app_data / 'recordings')
        
        selected_dir = self.browse_folder_with_file_preview(
            title="録音保存先フォルダを選択",
            initialdir=current_dir
        )
        
        if selected_dir:
            self.recording_output_dir_var.set(selected_dir)
    
    def open_recording_output_dir(self):
        """録音保存先フォルダを開く"""
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
    # v2.2 新機能: プリセット管理
    # ==========================================
    
    def build_preset_ui(self, parent):
        """プリセット管理UIを構築"""
        preset_frame = ttk.LabelFrame(parent, text="💾 プリセット管理", padding="5")
        preset_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(preset_frame, text="プリセット:").pack(side=tk.LEFT, padx=5)
        
        preset_combo = ttk.Combobox(preset_frame, textvariable=self.current_preset,
                                    values=list(self.presets.keys()),
                                    state='readonly', width=20)
        preset_combo.pack(side=tk.LEFT, padx=5)
        preset_combo.bind('<<ComboboxSelected>>', lambda e: self.load_preset())
        
        ttk.Button(preset_frame, text="💾 保存", command=self.save_preset, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="📝 名前変更", command=self.rename_preset, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="🗑️ 削除", command=self.delete_preset, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="➕ 新規", command=self.new_preset, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="❓", command=self.show_preset_help, width=3).pack(side=tk.LEFT, padx=2)
    
    def show_preset_help(self):
        """プリセット機能の使い方を表示"""
        messagebox.showinfo(
            "プリセット管理の使い方",
            "【プリセットとは？】\n"
            "よく使う設定（速度、音量、話者等）を保存して、\n"
            "ワンクリックで呼び出せる機能です。\n\n"
            "【使い方】\n"
            "1. 速度、音量、話者等を調整\n"
            "2. 「➕ 新規」をクリック\n"
            "3. 名前を入力（例: 解説動画用）\n"
            "4. 次回から選択するだけで適用！\n\n"
            "【デフォルトプリセット】\n"
            "初期設定が保存されています。\n"
            "・エンジン: Coqui TTS\n"
            "・速度: 1.0\n"
            "・音量: 1.0\n"
            "・形式: WAV\n\n"
            "【便利な使い方】\n"
            "・解説動画用（速度1.2、音量1.2）\n"
            "・雑談用（速度1.0、ずんだもん）\n"
            "・ニュース読み上げ用（速度1.3、四国めたん）"
        )
    
    def _get_current_settings(self):
        """現在の設定を取得（両方のエンジンの設定を保存）"""
        settings = {
            'engine': self.engine_var.get(),
            'speed': self.speed_var.get(),
            'volume': self.volume_var.get(),
            'pitch': self.pitch_var.get(),
            'intonation': self.intonation_var.get(),
            'pre_silence': self.pre_silence_var.get(),
            'post_silence': self.post_silence_var.get(),
            'format': self.format_var.get(),
            'prefix': self.prefix_var.get()  # 接頭辞を追加
        }
        
        # Coqui TTS設定
        if hasattr(self, 'coqui_speaker_var'):
            settings['coqui_speaker'] = self.coqui_speaker_var.get()
        if hasattr(self, 'language_var'):
            settings['language'] = self.language_var.get()
        
        # VOICEVOX設定
        if hasattr(self, 'vv_speaker_var'):
            settings['voicevox_speaker'] = self.vv_speaker_var.get()  # 表示用（"四国めたん (ID: 2)"）
            settings['voicevox_speaker_id'] = self.get_speaker_id()   # ID（2）
        
        return settings
    
    def _apply_settings(self, settings):
        """設定を適用（両方のエンジンの設定に対応）"""
        self.engine_var.set(settings.get('engine', 'coqui'))
        self.update_ui_state()
        
        # Coqui TTS設定
        if settings.get('coqui_speaker'):
            self.coqui_speaker_var.set(settings['coqui_speaker'])
        if settings.get('language'):
            self.language_var.set(settings['language'])
        
        # VOICEVOX設定
        if settings.get('voicevox_speaker'):
            self.vv_speaker_var.set(settings['voicevox_speaker'])
        
        # 共通パラメータ
        self.speed_var.set(settings.get('speed', 1.0))
        self.volume_var.set(settings.get('volume', 1.0))
        self.pitch_var.set(settings.get('pitch', 0.0))
        self.intonation_var.set(settings.get('intonation', 1.0))
        self.pre_silence_var.set(settings.get('pre_silence', 0.1))
        self.post_silence_var.set(settings.get('post_silence', 0.1))
        self.format_var.set(settings.get('format', 'wav'))
        self.prefix_var.set(settings.get('prefix', 'voice'))  # 接頭辞を適用
    
    def save_preset(self):
        """現在の設定をプリセットとして保存"""
        preset_name = self.current_preset.get()
        if not preset_name:
            messagebox.showwarning("警告", "プリセット名を選択してください")
            return
        
        self.presets[preset_name] = self._get_current_settings()
        self.config['presets'] = self.presets
        self.save_config()
        messagebox.showinfo("保存完了", f"プリセット「{preset_name}」を保存しました")
    
    def load_preset(self):
        """プリセットを読み込んで適用"""
        preset_name = self.current_preset.get()
        if preset_name not in self.presets:
            return
        
        settings = self.presets[preset_name]
        self._apply_settings(settings)
        self.status_bar.config(text=f"プリセット「{preset_name}」を適用しました")
    
    def new_preset(self):
        """新しいプリセットを作成"""
        dialog = tk.Toplevel(self.root)
        dialog.title("新しいプリセット")
        dialog.geometry("350x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="プリセット名:").pack(pady=10)
        
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        name_entry.pack(pady=5)
        name_entry.focus()
        
        def on_ok():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("警告", "名前を入力してください")
                return
            if name in self.presets:
                if not messagebox.askyesno("確認", f"「{name}」は既に存在します。上書きしますか？"):
                    return
            
            self.presets[name] = self._get_current_settings()
            self.current_preset.set(name)
            self.config['presets'] = self.presets
            self.save_config()
            dialog.destroy()
            messagebox.showinfo("作成完了", f"プリセット「{name}」を作成しました")
            
            # コンボボックス更新
            for widget in self.root.winfo_children():
                self._update_preset_combo(widget, list(self.presets.keys()))
        
        ttk.Button(dialog, text="OK", command=on_ok, width=15).pack(pady=10)
    
    def _update_preset_combo(self, widget, values):
        """プリセットコンボボックスを再帰的に更新"""
        if isinstance(widget, ttk.Combobox) and widget.cget('textvariable') == str(self.current_preset):
            widget['values'] = values
        for child in widget.winfo_children():
            self._update_preset_combo(child, values)
    
    def rename_preset(self):
        """プリセット名を変更"""
        old_name = self.current_preset.get()
        if old_name == 'デフォルト':
            messagebox.showwarning("警告", "デフォルトプリセットは名前変更できません")
            return
        if old_name not in self.presets:
            messagebox.showwarning("警告", "プリセットを選択してください")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("プリセット名変更")
        dialog.geometry("350x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="新しい名前:").pack(pady=10)
        
        name_var = tk.StringVar(value=old_name)
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        name_entry.pack(pady=5)
        name_entry.focus()
        name_entry.select_range(0, tk.END)
        
        def on_ok():
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showwarning("警告", "名前を入力してください")
                return
            if new_name in self.presets and new_name != old_name:
                messagebox.showwarning("警告", f"「{new_name}」は既に存在します")
                return
            
            self.presets[new_name] = self.presets.pop(old_name)
            self.current_preset.set(new_name)
            self.config['presets'] = self.presets
            self.save_config()
            dialog.destroy()
            messagebox.showinfo("変更完了", f"「{old_name}」→「{new_name}」に変更しました")
            
            # コンボボックス更新
            for widget in self.root.winfo_children():
                self._update_preset_combo(widget, list(self.presets.keys()))
        
        ttk.Button(dialog, text="OK", command=on_ok, width=15).pack(pady=10)
    
    def delete_preset(self):
        """プリセットを削除"""
        preset_name = self.current_preset.get()
        if preset_name == 'デフォルト':
            messagebox.showwarning("警告", "デフォルトプリセットは削除できません")
            return
        if preset_name not in self.presets:
            messagebox.showwarning("警告", "プリセットを選択してください")
            return
        
        if messagebox.askyesno("確認", f"プリセット「{preset_name}」を削除しますか？"):
            del self.presets[preset_name]
            self.current_preset.set('デフォルト')
            self.config['presets'] = self.presets
            self.save_config()
            messagebox.showinfo("削除完了", f"プリセット「{preset_name}」を削除しました")
            
            # コンボボックス更新
            for widget in self.root.winfo_children():
                self._update_preset_combo(widget, list(self.presets.keys()))
    
    # ==========================================
    # v2.2 新機能: 音声プレビュー
    # ==========================================
    
    def preview_voice(self):
        """最初の30文字だけ生成してプレビュー再生"""
        try:
            full_text = self.text_input.get('1.0', tk.END).strip()
            if not full_text:
                messagebox.showwarning("警告", "テキストを入力してください")
                return
            
            preview_text = full_text[:30].strip()
            if not preview_text:
                return
            
            self.status_bar.config(text="🔊 プレビュー生成中...")
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
            self.status_bar.config(text="✓ プレビュー再生完了")
            
        except Exception as e:
            messagebox.showerror("エラー", f"プレビュー生成エラー:\n{str(e)}")
            self.status_bar.config(text="✗ プレビュー失敗")
    
    def _play_audio(self, audio_path):
        """音声ファイルを再生"""
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(audio_path)
            elif system == "Darwin":
                subprocess.Popen(["afplay", str(audio_path)])
            else:
                subprocess.Popen(["aplay", str(audio_path)])
        except Exception as e:
            messagebox.showerror("再生エラー", f"音声再生に失敗しました:\n{str(e)}")
    
    def show_preview_help(self):
        """プレビュー機能の使い方を表示"""
        messagebox.showinfo(
            "プレビュー機能の使い方",
            "【プレビューとは？】\n"
            "設定を確認するために、最初の30文字だけを\n"
            "高速で音声生成＆再生する機能です。\n\n"
            "【特徴】\n"
            "・生成時間: 約3秒（全文生成は数十秒）\n"
            "・生成範囲: 最初の30文字のみ\n"
            "・設定反映: 速度、音量、ピッチ、話者など全設定を反映\n"
            "・自動再生: 生成後すぐに再生\n"
            "・何度でもOK: 設定を変えて何度でも試せる\n\n"
            "【保存場所】\n"
            "一時ファイル: user_data/preview_temp.wav\n"
            "※ 出力フォルダには保存されません\n"
            "※ Daily Loggerにも記録されません\n"
            "※ 何度実行しても上書きされます\n\n"
            "【本番生成との違い】\n"
            "┌────────────┬─────────┬─────────┐\n"
            "│ 項目       │ プレビュー│ 本番生成 │\n"
            "├────────────┼─────────┼─────────┤\n"
            "│ 生成範囲   │ 30文字   │ 全文     │\n"
            "│ 保存先     │ 一時     │ 出力先   │\n"
            "│ Logger記録 │ なし     │ あり     │\n"
            "│ ファイル名 │ 固定     │ 連番     │\n"
            "│ 用途       │ 設定確認 │ 最終出力 │\n"
            "└────────────┴─────────┴─────────┘\n\n"
            "【使い方】\n"
            "1. テキスト入力（全文でOK）\n"
            "2. 設定を調整（速度、音量、話者等）\n"
            "3. 「🔊 プレビュー」クリック\n"
            "4. 自動再生 → 設定を確認\n"
            "5. 気に入らなければ設定変更して再プレビュー\n"
            "6. OK！ → 「🎵 音声生成開始」で本番生成\n\n"
            "【便利な使い方】\n"
            "・速度調整: 1.0 → 1.2 → 1.5と試す\n"
            "・話者変更: めたん → ずんだもん → つむぎ\n"
            "・音量確認: 小さすぎる/大きすぎるを確認\n"
            "・言語確認: Coqui TTSの発音をチェック\n\n"
            "【時間節約の例】\n"
            "全文生成で試行錯誤:\n"
            "  60秒 × 5回 = 300秒（5分）\n"
            "プレビューで試行錯誤:\n"
            "  3秒 × 5回 = 15秒\n"
            "→ 285秒（約5分）節約！\n\n"
            "【ヒント】\n"
            "・設定が決まったらプリセット保存すると便利\n"
            "・30文字以下のテキストでも動作します\n"
            "・エラーが出たら設定を見直してください"
        )
    
    # ==========================================
    # v2.2 新機能: バッチ処理（STT）
    # ==========================================
    
    def batch_transcribe(self):
        """複数の音声ファイルを一括文字起こし"""
        file_paths = filedialog.askopenfilenames(
            title="音声ファイルを選択（複数可）",
            filetypes=[
                ("音声ファイル", "*.mp3 *.wav *.m4a *.flac *.ogg *.mp4 *.mkv *.avi"),
                ("すべてのファイル", "*.*")
            ]
        )
        
        if not file_paths:
            return
        
        output_dir = self.browse_folder_with_file_preview(
            title="バッチ処理の保存先フォルダを選択"
        )
        if not output_dir:
            return
        
        output_dir = Path(output_dir)
        self.transcribe_button.config(state='disabled')
        self.transcription_result.delete('1.0', tk.END)
        
        def worker():
            try:
                from whisper_engine import WhisperEngine
                
                total = len(file_paths)
                model_size = self.whisper_model_var.get()
                language = self.whisper_language_var.get().split(' - ')[0]
                output_format = self.whisper_format_var.get()
                
                if not self.whisper_engine or self.whisper_engine.model_size != model_size:
                    self.root.after(0, lambda: self.transcription_result.insert(
                        tk.END, f"🔧 Whisperエンジンを初期化中（{model_size}）...\n"))
                    self.whisper_engine = WhisperEngine(model_size=model_size, device='auto')
                
                for i, file_path in enumerate(file_paths, 1):
                    file_path = Path(file_path)
                    self.root.after(0, lambda i=i, t=total, n=file_path.name: 
                                  self.transcription_result.insert(tk.END, f"\n[{i}/{t}] {n}\n"))
                    
                    result = self.whisper_engine.transcribe(file_path, language=language, output_format=output_format)
                    
                    # 拡張子を.txtに統一（output_formatが"text"でも.txtで保存）
                    ext = "txt" if output_format == "text" else output_format
                    output_file = output_dir / f"{file_path.stem}.{ext}"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(result)
                    
                    self.root.after(0, lambda f=output_file: 
                                  self.transcription_result.insert(tk.END, f"  ✓ 保存: {f.name}\n"))
                
                self.root.after(0, lambda: self.transcription_result.insert(
                    tk.END, f"\n{'='*60}\n✅ 一括処理完了: {total}ファイル\n"))
                
                # 完了ダイアログで次の手順を案内
                def show_completion():
                    result = messagebox.askyesno(
                        "完了", 
                        f"{total}ファイルの文字起こしが完了しました\n"
                        f"保存先: {output_dir}\n\n"
                        "次に音声化しますか？\n"
                        "「はい」→ TTSタブの「フォルダ一括読み込み」を使用してください",
                        icon='info'
                    )
                    if result:
                        # TTSタブに切り替え
                        self.notebook.select(1)
                        messagebox.showinfo(
                            "案内",
                            f"TTSタブで「📂 フォルダ一括読み込み」ボタンをクリックし、\n"
                            f"以下のフォルダを選択してください：\n\n{output_dir}\n\n"
                            f"※ テキストが入力欄に表示されるので、確認・修正後に\n"
                            f"  「🎵 音声生成開始」ボタンを押してください"
                        )
                
                self.root.after(0, show_completion)
                
            except Exception as e:
                error_msg = f"エラー: {str(e)}"
                self.root.after(0, lambda msg=error_msg: 
                              self.transcription_result.insert(tk.END, f"\n❌ {msg}\n"))
            finally:
                self.root.after(0, lambda: self.transcribe_button.config(state='normal'))
        
        threading.Thread(target=worker, daemon=True).start()
    
    # ==========================================
    # v2.2 新機能: バッチ処理（TTS）
    # ==========================================
    
    def batch_generate(self):
        """フォルダ内のテキストファイルを一括読み込み（v2.2改善版）"""
        folder_path = self.browse_folder_with_file_preview(
            title="テキストファイルが入ったフォルダを選択"
        )
        
        if not folder_path:
            return
        
        folder_path = Path(folder_path)
        # ログファイル（YYYYMMDD_log.txt）を除外
        all_txt_files = list(folder_path.glob("*.txt"))
        txt_files = [f for f in all_txt_files if not f.name.endswith('_log.txt')]
        
        if not txt_files:
            messagebox.showwarning(
                "警告", 
                f"テキストファイル(.txt)が見つかりません\n\n"
                f"フォルダ: {folder_path}\n\n"
                f"※ STTタブで「テキスト」形式で保存したファイルは.txt拡張子になります\n"
                f"※ ログファイル（_log.txt）は自動的に除外されます"
            )
            return
        
        # ファイル数確認
        if not messagebox.askyesno("確認", 
            f"{len(txt_files)}個のテキストファイルが見つかりました。\n\n"
            f"テキスト入力欄に読み込みますか？\n"
            f"（現在のテキストは上書きされます）"):
            return
        
        # 全ファイルを読み込んで結合
        all_texts = []
        for txt_file in sorted(txt_files):  # ファイル名順にソート
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                if text:
                    all_texts.append(text)
            except Exception as e:
                messagebox.showerror("エラー", f"ファイル読み込みエラー:\n{txt_file.name}\n{str(e)}")
                return
        
        if not all_texts:
            messagebox.showwarning("警告", "読み込めるテキストがありませんでした")
            return
        
        # テキスト入力欄をクリアして、全テキストを空行で区切って表示
        self.text_input.delete('1.0', tk.END)
        combined_text = '\n\n'.join(all_texts)
        self.text_input.insert('1.0', combined_text)
        
        # ステータスバー更新
        segment_count = len(all_texts)
        self.status_bar.config(text=f"✓ {len(txt_files)}ファイルを読み込みました（{segment_count}セグメント）")
        
        # 案内メッセージを表示
        messagebox.showinfo(
            "読み込み完了", 
            f"✅ {len(txt_files)}個のファイルを読み込みました\n"
            f"📝 {segment_count}個のセグメント（空行で区切られた部分）\n\n"
            f"【次のステップ】\n"
            f"1. テキスト入力欄を確認してください\n"
            f"2. 必要があれば修正してください\n"
            f"3. 保存先と保存名を確認してください\n"
            f"4. 「🎵 音声生成開始」ボタンを押してください\n\n"
            f"※ 通常の処理フローで進行状況が確認できます"
        )

    
    # ==========================================
    # v2.2 新機能: テキスト履歴
    # ==========================================
    
    def save_to_history(self, text):
        """テキストを履歴に保存（最大10件）"""
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
        """テキスト履歴を表示するダイアログ"""
        if not self.text_history:
            messagebox.showinfo("履歴", "履歴はまだありません")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("テキスト履歴")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="最近使ったテキスト（ダブルクリックで適用）", 
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
            messagebox.showinfo("適用", "テキストを適用しました")
        
        listbox.bind('<Double-Button-1>', on_select)
        
        ttk.Button(dialog, text="閉じる", command=dialog.destroy, width=10).pack(pady=10)
    
    # ==========================================
    # v2.2 新機能: テンプレート
    # ==========================================
    
    def save_template(self):
        """現在のテキストをテンプレートとして保存"""
        text = self.text_input.get('1.0', tk.END).strip()
        if not text:
            messagebox.showwarning("警告", "テキストを入力してください")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("テンプレート保存")
        dialog.geometry("350x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="テンプレート名:").pack(pady=10)
        
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        name_entry.pack(pady=5)
        name_entry.focus()
        
        def on_ok():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("警告", "名前を入力してください")
                return
            
            self.templates[name] = text
            self.config['templates'] = self.templates
            self.save_config()
            dialog.destroy()
            messagebox.showinfo("保存完了", f"テンプレート「{name}」を保存しました")
        
        ttk.Button(dialog, text="OK", command=on_ok, width=15).pack(pady=10)
    
    def load_template(self):
        """テンプレートを読み込んで適用"""
        if not self.templates:
            messagebox.showinfo("テンプレート", "保存されたテンプレートはありません")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("テンプレート読み込み")
        dialog.geometry("500x350")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="テンプレート（ダブルクリックで適用）", 
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
            messagebox.showinfo("適用", f"テンプレート「{name}」を適用しました")
        
        listbox.bind('<Double-Button-1>', on_select)
        
        # ボタンフレーム
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def delete_selected():
            """選択されたテンプレートを削除"""
            if not listbox.curselection():
                messagebox.showwarning("警告", "削除するテンプレートを選択してください")
                return
            
            index = listbox.curselection()[0]
            name = list(self.templates.keys())[index]
            
            # 削除確認
            result = messagebox.askyesno(
                "削除確認",
                f"テンプレート「{name}」を削除しますか？"
            )
            
            if result:
                # 削除実行
                del self.templates[name]
                self.save_config()  # 設定保存
                
                # Listbox更新
                listbox.delete(0, tk.END)
                for template_name in self.templates.keys():
                    listbox.insert(tk.END, template_name)
                
                messagebox.showinfo("削除完了", f"テンプレート「{name}」を削除しました")
                
                # テンプレートが空になったらダイアログを閉じる
                if not self.templates:
                    messagebox.showinfo("テンプレート", "すべてのテンプレートが削除されました")
                    dialog.destroy()
        
        ttk.Button(button_frame, text="🗑️ 削除", command=delete_selected, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="閉じる", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
    
    def show_template_help(self):
        """テンプレート機能の使い方を表示"""
        messagebox.showinfo(
            "テンプレート機能の使い方",
            "【テンプレートとは？】\n"
            "よく使う定型文（オープニング、締め等）を\n"
            "保存して、ワンクリックで呼び出せる機能です。\n\n"
            "【プリセットとの違い】\n"
            "・プリセット = 「どう読むか」（速度、音量、話者）\n"
            "・テンプレート = 「何を読むか」（テキスト内容）\n\n"
            "【使い方】\n"
            "《保存》\n"
            "1. よく使う定型文をテキスト入力欄に入力\n"
            "2. 「💾」ボタンをクリック\n"
            "3. 名前を入力（例: オープニング）\n"
            "4. 保存完了！\n\n"
            "《呼び出し》\n"
            "1. 「📝 テンプレート」ボタンをクリック\n"
            "2. 使いたいテンプレートを選択\n"
            "3. テキスト入力欄に自動挿入！\n"
            "4. 必要に応じて編集\n\n"
            "【便利な使い方】\n"
            "・オープニング（挨拶＋チャンネル紹介）\n"
            "  「こんにちは、〇〇チャンネルへようこそ...」\n\n"
            "・締めの言葉（チャンネル登録のお願い）\n"
            "  「今日の解説は以上です。チャンネル登録...」\n\n"
            "・自己紹介\n"
            "  「このチャンネルでは〇〇について...」\n\n"
            "・注意書き\n"
            "  「この動画の情報は〇〇年〇月時点のもので...」\n\n"
            "【プリセットと組み合わせて使う】\n"
            "1. テンプレート「オープニング」で定型文挿入\n"
            "2. 〇〇部分を編集\n"
            "3. プリセット「解説動画用」で声の設定\n"
            "4. 音声生成 → 最速・最高品質！\n\n"
            "【ヒント】\n"
            "・〇〇や【 】で置き換え箇所を明示すると便利\n"
            "・シリーズごとにテンプレートを作成\n"
            "・複数の定型文を組み合わせて使用"
        )
    
    # ==========================================
    # v2.2 新機能: 自動バックアップ
    # ==========================================
    
    def start_auto_backup(self):
        """自動バックアップを開始（1分ごと）"""
        if self.auto_backup_enabled:
            self.auto_backup()
            self.backup_timer_id = self.root.after(60000, self.start_auto_backup)
    
    def auto_backup(self):
        """テキストを自動バックアップ"""
        try:
            text = self.text_input.get('1.0', tk.END).strip()
            if text and len(text) > 10:
                backup_file = self.app_data / "text_backup.txt"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(text)
        except:
            pass
    
    def restore_backup(self):
        """バックアップからテキストを復元"""
        backup_file = self.app_data / "text_backup.txt"
        
        if not backup_file.exists():
            messagebox.showinfo("バックアップ", "バックアップファイルが見つかりません")
            return
        
        if messagebox.askyesno("確認", "バックアップから復元しますか?\n現在のテキストは上書きされます"):
            with open(backup_file, 'r', encoding='utf-8') as f:
                text = f.read()
            self.text_input.delete('1.0', tk.END)
            self.text_input.insert('1.0', text)
            messagebox.showinfo("復元完了", "バックアップを復元しました")


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
