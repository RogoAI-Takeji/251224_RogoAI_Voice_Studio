# 変更履歴 / Changelog

## 🌐 Language / 言語

- [日本語版 CHANGELOG](CHANGELOG_JP.md) ← 現在のページ
- [English CHANGELOG](CHANGELOG_EN.md)

---

## [v2.4] - 2025-01-06

### ✨ 新機能
- **EXE化対応完了**: PyInstallerによる実行可能ファイル化
  - JP版/EN版それぞれ独立したEXEを提供
  - `_internal`フォルダとセットで配布（onedirモード）
  - ffmpeg、ffprobeを同梱
  - faster-whisper、TTS、torch等の全依存関係を統合

### 🔧 技術的改善
- PyInstallerビルドスクリプトの最適化
- GGUFモデル対応の依存関係を追加
- hidden-importの設定を最適化

### 📦 配布方法の変更
- **重要**: EXEファイルと`_internal`フォルダは必ずセットで配布
- ZIPファイルに親フォルダごと圧縮して提供
- ユーザーは解凍後、フォルダ内のEXEを実行

---

## [v2.3] - 2025-01-04

### ✨ 新機能
- Whisper文字起こし機能の安定化
- モデル選択UIの改善
- 処理速度の最適化

---

## [v2.2] - 2025-01-03

### ✨ 新機能
- faster-whisper統合による高速文字起こし
- 3種類のモデルサイズ選択機能（base/medium/large-v3）
- デフォルトモデルをbaseに設定

### 🎯 使いやすさ向上
- モデル選択UIの実装
- mediumモデルで95%の高精度を達成

---

## [v2.1] - 2025-01-02

### ✨ 新機能
- **Whisper文字起こし機能追加** (Phase 2)
  - MP4動画から自動文字起こし
  - faster-whisperエンジン統合
  - モデルサイズ選択可能

---

## [v2.0] - 2025-01-01

### ✨ 新機能
- **Daily Logger機能** (Phase 1完了)
  - ログファイルを音声ファイルと同じ出力フォルダに自動保存
  - 処理完了時に通知メッセージ表示
  - 日英両バージョン対応

### 🎯 使いやすさ向上
- ファイル管理の簡素化（ログと音声を同じ場所に保存）
- ユーザーフィードバックの即時表示

---

## [v1.9.2] - 2024-12-25

### 最終Slimバージョン
- VOICEVOX、Coqui TTS対応
- Python環境での実行
- バッチファイルによるセットアップ
- 基本的な音声合成機能

---

## EXE化に関する重要な注意事項

### 配布ファイル構造
```
RogoAI_Voice_Studio_JP/  ← このフォルダごとZIP圧縮
├── rogoai_voice_studio_v2.4_JP.exe  ← 起動ファイル
└── _internal/  ← 本体（絶対に削除・分離禁止）
    ├── Python実行環境
    ├── AIライブラリ（PyTorch、TTS等）
    └── 依存DLL類
```

### ⚠️ 警告
1. **`_internal`フォルダは絶対に削除・移動・分離しないでください**
2. EXEファイルと`_internal`フォルダは必ず同じ階層に配置
3. EXEファイルのみをデスクトップに置きたい場合は、**ショートカット**を作成してください

### 📋 ビルドコマンド（開発者向け）

#### JP版
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

#### EN版
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

## バージョン番号の意味

- **メジャー**: 大規模な機能追加や破壊的変更（例: v1 → v2）
- **マイナー**: 新機能追加（例: v2.0 → v2.1）
- **パッチ**: バグ修正や小規模改善（例: v2.1 → v2.1.1）

---

## リリースノート

各バージョンの詳細なリリースノートは[GitHub Releases](https://github.com/RogoAI-Takeji/Voice-Studio/releases)をご覧ください。
