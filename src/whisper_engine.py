"""
whisper_engine.py

faster-whisperを使った音声認識エンジン

Author: RogoAI
Version: 1.0
"""

from faster_whisper import WhisperModel
import torch
from pathlib import Path
import warnings

# FutureWarningを抑制
warnings.filterwarnings("ignore", category=FutureWarning)


class WhisperEngine:
    """faster-whisperを使った高速音声認識エンジン"""
    
    AVAILABLE_MODELS = ['base', 'medium', 'large-v3']
    
    SUPPORTED_LANGUAGES = {
        'ja': '日本語',
        'en': 'English',
        'zh': '中文',
        'ko': '한국어',
        'fr': 'Français',
        'de': 'Deutsch',
        'es': 'Español',
        'it': 'Italiano',
        'pt': 'Português',
        'ru': 'Русский'
    }
    
    MODEL_INFO = {
        'base': {
            'size': '~140MB',
            'vram': '~1GB',
            'ram': '~2GB',
            'accuracy': '85%',
            'speed': '10x',
            'description': '高速・軽量。短い音声や低スペックPC向け'
        },
        'medium': {
            'size': '~1.5GB',
            'vram': '~5GB',
            'ram': '~8GB',
            'accuracy': '95%',
            'speed': '4x',
            'description': '推奨。精度と速度のバランスが良い'
        },
        'large-v3': {
            'size': '~3GB',
            'vram': '~10GB',
            'ram': '~16GB',
            'accuracy': '98%',
            'speed': '1x',
            'description': '最高精度。長時間・複雑な音声向け'
        }
    }
    
    def __init__(self, model_size='base', device='auto'):
        """
        初期化
        
        Args:
            model_size: 'base', 'medium', 'large-v3'
            device: 'auto', 'cuda', 'cpu'
        """
        if model_size not in self.AVAILABLE_MODELS:
            raise ValueError(f"Invalid model_size. Choose from {self.AVAILABLE_MODELS}")
        
        self.model_size = model_size
        self.device = self._determine_device(device)
        self.model = None
        
        print(f"[WhisperEngine] Initialized with model='{model_size}', device='{self.device}'")
    
    def _determine_device(self, device):
        """デバイスの自動判定"""
        if device == 'auto':
            cuda_available = torch.cuda.is_available()
            selected_device = 'cuda' if cuda_available else 'cpu'
            if cuda_available:
                print(f"[WhisperEngine] CUDA available: {torch.cuda.get_device_name(0)}")
            else:
                print("[WhisperEngine] CUDA not available, using CPU")
            return selected_device
        return device
    
    def load_model(self, progress_callback=None):
        """
        モデルをロード (初回はダウンロード)
        
        Args:
            progress_callback: 進捗通知用コールバック関数
            
        Returns:
            bool: 成功したらTrue
        """
        if progress_callback:
            progress_callback(f"モデル '{self.model_size}' をロード中...")
        
        try:
            # compute_typeの決定
            if self.device == 'cuda':
                compute_type = 'float16'  # GPU: float16
            else:
                compute_type = 'int8'  # CPU: int8
            
            print(f"[WhisperEngine] Loading model with compute_type='{compute_type}'")
            
            # モデルロード
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=compute_type,
                download_root=None  # デフォルトキャッシュディレクトリを使用
            )
            
            if progress_callback:
                progress_callback(f"モデル '{self.model_size}' ロード完了")
            
            print(f"[WhisperEngine] Model '{self.model_size}' loaded successfully")
            return True
            
        except Exception as e:
            error_msg = f"モデルロードエラー: {str(e)}"
            print(f"[WhisperEngine] {error_msg}")
            
            if progress_callback:
                progress_callback(error_msg)
            
            return False
    
    def transcribe(self, audio_path, language='ja', output_format='text', 
                   progress_callback=None):
        """
        音声ファイルを文字起こし
        
        Args:
            audio_path: 音声ファイルのパス (str or Path)
            language: 言語コード ('ja', 'en', etc.)
            output_format: 'text' または 'srt'
            progress_callback: 進捗通知用コールバック関数
            
        Returns:
            str: 文字起こし結果
            
        Raises:
            Exception: 処理に失敗した場合
        """
        # モデルがロードされていない場合はロード
        if not self.model:
            success = self.load_model(progress_callback)
            if not success:
                raise Exception("モデルのロードに失敗しました")
        
        if progress_callback:
            progress_callback("文字起こし処理を開始...")
        
        try:
            audio_path = str(audio_path)
            print(f"[WhisperEngine] Transcribing: {audio_path}")
            print(f"[WhisperEngine] Language: {language}, Format: {output_format}")
            
            # 文字起こし実行
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                vad_filter=True,  # VAD (Voice Activity Detection) で無音部分を除去
                word_timestamps=False,  # 単語レベルのタイムスタンプは不要
                beam_size=5,  # ビームサーチのサイズ
                best_of=5,  # ベストN個から選択
                temperature=0.0,  # 確定的な出力
                condition_on_previous_text=True  # 前のテキストを条件に含める
            )
            
            # 検出された言語を表示
            detected_lang = info.language
            detected_prob = info.language_probability
            print(f"[WhisperEngine] Detected language: {detected_lang} (probability: {detected_prob:.2f})")
            
            if progress_callback:
                progress_callback(f"言語検出: {detected_lang} ({detected_prob*100:.1f}%)")
            
            # 出力形式に応じて処理
            if output_format == 'srt':
                result = self._generate_srt(segments, progress_callback)
            else:
                result = self._generate_text(segments, progress_callback)
            
            print(f"[WhisperEngine] Transcription completed. Length: {len(result)} chars")
            return result
            
        except Exception as e:
            error_msg = f"文字起こしエラー: {str(e)}"
            print(f"[WhisperEngine] {error_msg}")
            
            if progress_callback:
                progress_callback(error_msg)
            
            raise Exception(error_msg)
    
    def _generate_text(self, segments, progress_callback):
        """
        テキスト形式で出力
        
        Args:
            segments: Whisperのセグメントイテレータ
            progress_callback: 進捗通知用コールバック
            
        Returns:
            str: 改行区切りのテキスト
        """
        result = []
        segment_count = 0
        
        for segment in segments:
            text = segment.text.strip()
            if text:  # 空のセグメントは除外
                result.append(text)
                segment_count += 1
                
                if progress_callback and segment_count % 10 == 0:
                    progress_callback(f"処理中: {segment_count}セグメント")
        
        if progress_callback:
            progress_callback(f"完了: {segment_count}セグメント処理")
        
        return '\n'.join(result)
    
    def _generate_srt(self, segments, progress_callback):
        """
        SRT字幕形式で出力
        
        Args:
            segments: Whisperのセグメントイテレータ
            progress_callback: 進捗通知用コールバック
            
        Returns:
            str: SRT形式の字幕
        """
        result = []
        segment_count = 0
        
        for i, segment in enumerate(segments, 1):
            text = segment.text.strip()
            if not text:  # 空のセグメントは除外
                continue
            
            start = self._format_timestamp(segment.start)
            end = self._format_timestamp(segment.end)
            
            # SRTフォーマット
            result.append(f"{i}")
            result.append(f"{start} --> {end}")
            result.append(text)
            result.append("")  # 空行
            
            segment_count += 1
            
            if progress_callback and segment_count % 10 == 0:
                progress_callback(f"字幕生成中: {segment_count}セグメント")
        
        if progress_callback:
            progress_callback(f"完了: {segment_count}セグメント処理")
        
        return '\n'.join(result)
    
    def _format_timestamp(self, seconds):
        """
        秒数をSRT形式のタイムスタンプに変換
        
        Args:
            seconds: 秒数 (float)
            
        Returns:
            str: "HH:MM:SS,mmm" 形式のタイムスタンプ
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def get_model_info(self):
        """
        現在のモデル情報を取得
        
        Returns:
            dict: モデル情報
        """
        return {
            'model_size': self.model_size,
            'device': self.device,
            'loaded': self.model is not None,
            'details': self.MODEL_INFO.get(self.model_size, {})
        }
    
    @classmethod
    def get_all_model_info(cls):
        """
        全モデルの情報を取得
        
        Returns:
            dict: 全モデルの情報
        """
        return cls.MODEL_INFO
    
    def unload_model(self):
        """モデルをメモリから解放"""
        if self.model:
            del self.model
            self.model = None
            print("[WhisperEngine] Model unloaded")
    
    def __del__(self):
        """デストラクタ - モデルを解放"""
        self.unload_model()


# テスト用
if __name__ == "__main__":
    print("=== WhisperEngine Test ===")
    
    # エンジン初期化
    engine = WhisperEngine(model_size='base', device='auto')
    
    # モデル情報表示
    info = engine.get_model_info()
    print(f"\nModel Info: {info}")
    
    # 全モデル情報表示
    all_info = WhisperEngine.get_all_model_info()
    print(f"\nAll Models Info:")
    for model, details in all_info.items():
        print(f"  {model}: {details['description']}")
    
    # テスト音声ファイルがあれば文字起こし
    test_audio = Path("test_audio.mp3")
    if test_audio.exists():
        print(f"\nTranscribing: {test_audio}")
        
        def progress(msg):
            print(f"  Progress: {msg}")
        
        try:
            result = engine.transcribe(test_audio, language='ja', 
                                      output_format='text',
                                      progress_callback=progress)
            print(f"\nResult:\n{result}")
        except Exception as e:
            print(f"\nError: {e}")
    else:
        print(f"\nTest audio file not found: {test_audio}")
    
    print("\n=== Test Complete ===")