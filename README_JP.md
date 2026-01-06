# RogoAI Voice Studio v2.4

![Version](https://img.shields.io/badge/version-2.4-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

## 🌐 Language / 言語

- [日本語版 README](README_JP.md) ← 現在のページ
- [English README](README_EN.md)

---

**シニアでも簡単に使えるAI音声合成スタジオ**

VOICEVOX、Coqui TTS、faster-whisperを統合した、シニア向けの使いやすい音声合成アプリケーションです。

---

## ✨ 主な機能

### 🎤 音声合成
- **VOICEVOX**: 高品質な日本語音声合成
- **Coqui TTS**: 多言語対応の音声合成エンジン
- 感情表現、話速、音高の調整機能

### 📝 Whisper文字起こし (v2.1+)
- MP4動画から自動文字起こし
- 3種類の精度モデル選択（base/medium/large-v3）
- 95%の高精度（mediumモデル）

### 📊 Daily Logger (v2.0+)
- 処理ログを音声ファイルと同じフォルダに自動保存
- 処理完了時の通知機能
- 日時付きログファイル

---

## 📦 ダウンロード

### ⚡ EXE版（推奨・初心者向け）

**v2.4以降はEXE版を推奨します** - Python環境不要、ダウンロードして即利用可能！

#### 📥 [最新版をダウンロード](https://github.com/RogoAI-Takeji/Voice-Studio/releases/latest)

- **日本語版**: `rogoai_voice_studio_v2.4_JP.zip`
- **English Version**: `rogoai_voice_studio_v2.4_EN.zip`

### 🐍 Python版（上級者向け）

Python環境がある方は、ソースコードから実行も可能です。

```bash
git clone https://github.com/RogoAI-Takeji/Voice-Studio.git
cd Voice-Studio/src
```

---

## 🚀 インストール方法（EXE版）

### ステップ1: ダウンロード
1. [Releases](https://github.com/RogoAI-Takeji/Voice-Studio/releases)から最新版のZIPファイルをダウンロード
2. 日本語版は`rogoai_voice_studio_v2.4_JP.zip`を選択

### ステップ2: 解凍
1. ダウンロードしたZIPファイルを右クリック
2. 「すべて展開」を選択
3. 好きな場所に展開（例: デスクトップ、ドキュメント）

### ステップ3: 実行
1. 展開されたフォルダを開く
2. `rogoai_voice_studio_v2.4_JP.exe`をダブルクリック
3. アプリが起動します！

### ⚠️ 重要な注意事項

**`_internal`フォルダは絶対に削除・移動しないでください！**

```
RogoAI_Voice_Studio_JP/  ← このフォルダごと保管
├── rogoai_voice_studio_v2.4_JP.exe  ← これを起動
└── _internal/  ← これは絶対に触らない！
```

#### デスクトップにアイコンを置きたい場合
1. EXEファイルを右クリック
2. 「ショートカットの作成」を選択
3. 作成されたショートカットをデスクトップに移動

**注意**: EXEファイル本体を移動すると動作しなくなります！

---

## 📖 使い方

### 基本的な使い方

#### 1. 音声合成（VOICEVOX）
1. テキストボックスに読み上げたい文章を入力
2. VOICEVOXのキャラクター・感情を選択
3. 話速・音高を調整（任意）
4. 「音声生成」ボタンをクリック
5. 保存先を指定して完了

#### 2. 音声合成（Coqui TTS）
1. テキストボックスに読み上げたい文章を入力
2. Coqui TTSモデルを選択
3. 話速を調整（任意）
4. 「音声生成」ボタンをクリック
5. 保存先を指定して完了

#### 3. Whisper文字起こし (v2.1+)
1. 「Whisper」タブを開く
2. MP4動画ファイルを選択
3. モデルサイズを選択:
   - **base**: 高速（2-3分/10分動画）
   - **medium**: 高精度・推奨（5-7分/10分動画）
   - **large-v3**: 最高精度（10-15分/10分動画）
4. 「文字起こし開始」ボタンをクリック
5. SRTファイルが動画と同じフォルダに保存されます

### 📋 詳細な使い方

より詳しい使い方は、[docs/how_to_use.md](docs/how_to_use_JP.md)をご覧ください。

---

## 🔧 トラブルシューティング

### EXEが起動しない

#### 原因1: `_internal`フォルダがない
- **解決策**: ZIPファイルを再度ダウンロードして、正しく解凍してください

#### 原因2: セキュリティソフトがブロックしている
- **解決策**: セキュリティソフトの設定で、このアプリを許可してください

#### 原因3: Windows Defenderの警告
- **解決策**: 
  1. 「詳細情報」をクリック
  2. 「実行」をクリック
  3. これは署名なしアプリの標準的な警告です

### VOICEVOXエンジンが見つからない

#### VOICEVOXが未インストール
- **解決策**: [VOICEVOX公式サイト](https://voicevox.hiroshiba.jp/)からダウンロードしてインストール

#### VOICEVOXが起動していない
- **解決策**: VOICEVOXを起動してから、Voice Studioを使用してください

### Whisper処理が遅い

#### 原因: large-v3モデルを選択している
- **解決策**: mediumモデルに変更してください（精度95%で実用十分）

### ログファイルが見つからない

#### v2.0以降の動作
- **保存先**: 音声ファイルと同じフォルダ
- **ファイル名**: `voice_studio_log_YYYYMMDD_HHMMSS.txt`

---

## 🛠️ Python版のインストール（上級者向け）

### 必要環境
- Python 3.10以上
- pip（Pythonパッケージマネージャー）
- ffmpeg、ffprobe（音声処理用）

### インストール手順

```bash
# リポジトリをクローン
git clone https://github.com/RogoAI-Takeji/Voice-Studio.git
cd Voice-Studio

# 必要なパッケージをインストール
pip install -r requirements.txt

# アプリを起動（日本語版）
cd src
python rogoai_voice_studio_v2_4_JP.py

# または英語版
python rogoai_voice_studio_v2_4_EN.py
```

### ffmpegのインストール

#### Windows
1. [ffmpeg公式サイト](https://ffmpeg.org/download.html)からダウンロード
2. `ffmpeg.exe`と`ffprobe.exe`を`src/ffmpeg/`フォルダに配置

#### Mac/Linux
```bash
# Mac (Homebrew)
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

---

## 📚 ドキュメント

- [変更履歴](CHANGELOG_JP.md)
- [詳細な使い方](docs/how_to_use_JP.md)
- [よくある質問（FAQ）](docs/FAQ_JP.md)

---

## 🎬 チュートリアル動画

YouTubeで使い方を解説しています：

- [Voice Studio v2.4 基本操作](https://youtube.com/@RogoAI)
- [Whisper文字起こし機能の使い方](https://youtube.com/@RogoAI)

---

## 🤝 コントリビューション

プルリクエストやイシューの報告を歓迎します！

1. このリポジトリをフォーク
2. 新しいブランチを作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにプッシュ (`git push origin feature/AmazingFeature`)
5. プルリクエストを作成

---

## 📄 ライセンス

MITライセンスの下で配布されています。詳細は[LICENSE](LICENSE)ファイルをご覧ください。

---

## 🙏 謝辞

- [VOICEVOX](https://voicevox.hiroshiba.jp/) - 高品質な日本語音声合成
- [Coqui TTS](https://github.com/coqui-ai/TTS) - オープンソース音声合成エンジン
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - 高速音声認識
- [PyInstaller](https://pyinstaller.org/) - Pythonアプリのexe化

---

## 📧 お問い合わせ

- **YouTube**: [老後AI](https://youtube.com/@RogoAI)
- **GitHub Issues**: [問題報告](https://github.com/RogoAI-Takeji/Voice-Studio/issues)

---

## ⭐ スター・フォローをお願いします！

このプロジェクトが役に立ったら、ぜひGitHubでスターをつけてください！

[![Star on GitHub](https://img.shields.io/github/stars/RogoAI-Takeji/Voice-Studio.svg?style=social)](https://github.com/RogoAI-Takeji/Voice-Studio)

---

**Made with ❤️ by RogoAI-Takeji**

*シニアでも楽しめるAI開発を目指して*
