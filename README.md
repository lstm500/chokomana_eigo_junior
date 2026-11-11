# ちょこまな 英語（6歳・英語未経験から）

GitHub + Streamlit + Supabase 用の独立アプリです。添付の「ことばアプリ」の配色・2列カード・短いチャレンジ・メダル表示を参考にしています。既存のことば／そろばん／図形／ちょこまな本体は変更しません。

## 1. 実装している学習

| 項目 | やること | 初期1回の問題数 | 採点方法 |
|---|---|---:|---|
| きいて わかる | 英語の音を聞いて絵を選ぶ | 6 | 自動・初回回答 |
| まねして はなす | 英語を聞き、実際にまねする | 4 | 自己確認（客観的正答扱いしない） |
| ことばと え | 画像・日本語と英語の単語を結ぶ | 6 | 自動・初回回答 |
| もじと おと | 語頭文字と単語音、後期は短い単語を読む | 5 | 自動・初回回答 |
| やりとり | 英語を聞いて合う返答を選ぶ | 4 | 自動・初回回答 |
| よんで わかる | 文字と絵を結ぶ | 5 | 自動・初回回答 |
| アルファベット | 大文字と小文字を結ぶ | 6 | 自動・初回回答 |

全7項目×3段階＝**21メニュー・394問**（リリース時の教材バージョンは `app.py --catalog-count` で確認）。最初は「きいて わかる」「まねして はなす」を中心に1回5分前後から。アルファベットと読みは徐々に追加します。作文・タイピングは初期段階では実装しません。日本語と絵文字が見える問題は、完全な聞き取り能力の測定とは限りません。

音声出力には端末ブラウザの **Web Speech API** を使用します。音質・利用可能な声・マイク認識の可否は端末／ブラウザに依存します。音声認識のテキストは画面内だけに表示し、DBへ保存しません。通信がないと使えない音声エンジンもあります。音声APIの品質を母語話者の発音と同一視しないでください。

## 2. GitHub / Streamlit 初期設定

1. このフォルダの `app.py`、`requirements.txt`、`setup_supabase.sql`、`README.md`、`.gitignore`、`.streamlit/secrets.toml.example` を新しいGitHubリポジトリに置く。実行ファイルは **`app.py` 1本**です。
2. Supabaseプロジェクトの **SQL Editor** で `setup_supabase.sql` を実行する。既存ちょこまなのDBと共有する前提です。共通の `chokomana_learning_catalog` / `chokomana_learning_events` / `chokomana_stamps` は既存のものを利用し、既存テーブル・関数・過去データを上書きしません。新規Supabaseプロジェクトで利用する場合は、これらの共通テーブルが別途必要です。**SQLを適用するプロジェクトは必ず確認**してください。
3. Streamlit Community Cloudからリポジトリを指定し、main file pathを `app.py` に設定する。
4. Streamlit Secretsへ以下を設定する（実際のキーはGitHubに置かない）：
   ```toml
   SUPABASE_URL = "https://YOUR_PROJECT_REF.supabase.co"
   SUPABASE_SERVICE_ROLE_KEY = "YOUR_SERVER_ONLY_KEY"
   ENGLISH_APP_URL = "https://your-english-app.streamlit.app/" # 任意・台帳URL用
   CHOKOMANA_HUB_URL = "https://your-hub.streamlit.app/" # 任意・戻り先用
   ```
5. 起動して初回のメニューを開き、音声再生・問題回答・完了・スタンプを確認する。`chokomana_learning_catalog` には21メニュー・技能・394問を登録します。`english_attempts`／`chokomana_learning_events` に記録が保存されます。

Secretsが空の状態でも端末のlocalStorageで学習できますが、**Supabaseにも、ちょこまなにも記録されません**。端末で一時保存する記録はブラウザのデータ削除で消えます。Cloudで保存確認できたときのみ「保存しました」と表示します。

### 必要な権限とセキュリティ

`SUPABASE_SERVICE_ROLE_KEY` は **Streamlit Pythonサーバーでのみ使用**。HTML/JavaScript、リポジトリ、URLには送信しません。SQLはアプリ固有テーブルのRLSを有効化し、匿名アクセスの権限を撤回し、`service_role`へ明示的GRANTを付与します。既存共通テーブルには権限を勝手に追加しません。サービスキーでブラウザが指定した `profile_id` を無条件に信用しません。ログインなしの学習者識別には端末に生成した256ビット乱数のSHA256ハッシュを使います。

### 別端末・複数の子ども

端末をまたいだ自動復元、匿名履歴から既存ちょこまな利用者への自動統合は **未実装**です。同じ端末で別の子どもが使う場合は別のブラウザプロフィールを使用してください。別の学習者の履歴を誤って結合しないため、異なる学習者での自動再紐付けは拒否します。

## 3. ちょこまな連携用仕様（現時点で本体未変更）

- `schema_version=1` / `source_app=english` / `content_version=english-<教材ハッシュ>`。
- 共通テーブル `chokomana_learning_catalog`: `menu`・`skill`・`question`。メニューIDは `english.<category>.<difficulty>`、難易度は `beginner`・`intermediate`・`advanced`。教材の実件数・見積り時間（`duration_basis=provisional`）・技能・選択手順を登録します。
- 共通テーブル `chokomana_learning_events`: `session_started`, `item_presented`, `response_submitted`, `support_used`, `time_interval_closed`, `session_paused/resumed/ended`, `learning_activity`。`event_id`, `attempt_id`, `occurrence_id`, `segment_id` はUUID、時間は整数ミリ秒／UTC ISO8601 Z、`event_hash`は正規化ペイロードのSHA256。初回回答と再回答、ヒント／再生、異なる問題ID／同じ出題family／違う日を区別します。
- 共通テーブル `chokomana_stamps`: 完了時に1個、同じ `attempt_id` の再送では重複させません。英語版の段階は客観問題の**初回**正答率＝100%金、80%以上銀、60%以上銅、その他白です。発話の自己確認は白のみ。途中終了はメダルなし。
- 専用表 `english_attempts`: 実施を簡易集計して保存。学習計画側は**詳細分析を共通イベント／response_factsから再構成**してください。完成正答率だけで習得済みとしません。
- `time_interval_closed`: 実測可能な前景時間と `hidden/explicit_pause/blocking_wait` を区別します。不明な時間は `active_ms=null` とし計上しません。複数アプリ合算の重複除去は**ちょこまな側**で区間の和集合を取る設計です。
- 学習者本人の取得では、端末から受けた `profile_id` 単独を信用せず、学習者トークンに紐づいた本人確認を行ってください。詳細回答は一般公開しません。
- 任意の`?cm_launch=...`は将来の英語アプリ専用一回限り起動チケット。集約アプリ側が `source_app='english'` のチケットを発行できるようになって初めて利用可能です。**既存集約アプリは今回は変更していないため、実連携は未確認**です。`ENGLISH_APP_URL` 設定後の初回接続時に台帳を公開します（公開済み行のURL更新は別途管理者操作が必要）。

### 学習状況と「未判定」

ローカルの簡易目安では、客観的な初回答が8件以上、2日以上、異なる問題6件以上、教材に2種類以上のファミリーがあるとき2種類以上、正答率80%以上で次へと表示します。未達を苦手と断定せず、記録不足は未判定とします。新しい問題への転移や前提技能の成否などを確認しない限り習得を確定しません。最終的な計画作成・年齢×10分の上限は**集約アプリの役割**であり、英語版では実装していません。

## 4. テスト／制約

```bash
python -m py_compile app.py
python app.py --catalog-count
python -m pytest tests -q
streamlit run app.py
```

- 実ブラウザの画面遷移・問題の完了テストは `tests/browser_smoke.py`（Playwright）を参考に検証できます。
- 本アーティファクト作成時、テスト環境にStreamlitとSupabase SDKがなく、外部パッケージの取得もできなかったため、**Streamlit実サーバーの起動・実Supabaseへの書き込み・実際のブラウザ音声は未確認**です。静的検査、カリキュラム・保存形式のユニットテスト、ブラウザHTML操作テストは別途実施します。
- Supabase接続を設定しても SQL 未実行／テーブル権限不一致だと「端末保存・未連携」と表示されます。保存成功と偽って見せません。

## 実行環境と未確認事項（2026-11-12）

ソースコードのPythonユニットテストと、Chromiumの独立HTML画面操作テスト（開始→6問→再回答→結果）を実行済みです。実際のStreamlit・Supabaseに接続した書き込み、読み上げ音声の聴取、集約アプリからの起動、実機での時間計測と復元は未確認です。**既存DBの `chokomana_launch_tickets.source_app` と `chokomana_device_links.source_app` は現在 english を許さない制約**を持ちます。今回これを変更していないため、集約側のチケット起動は未連携であり、将来集約アプリ側との調整が必要です。
