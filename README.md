# step4-pos

要件定義書・システム仕様設計書に基づく、簡易POS（Lv2）実装です。  
構成は `Next.js (frontend)` + `FastAPI (backend)` + `MySQL` です。

## ディレクトリ構成

- `/pos-app/frontend` : Next.js フロントエンド
- `/pos-app/backend` : FastAPI バックエンド
- `/pos-app/backend/schema.sql` : 非破壊（`CREATE TABLE IF NOT EXISTS`）の初期化SQL
- `/.env.example` : 必要な環境変数テンプレート

## 事前準備

1. `.env.example` を `.env` にコピーし、**実際のDB接続情報は環境変数で設定**してください。
2. MySQLへ `pos-app/backend/schema.sql` を適用してください。

```bash
cp .env.example .env
mysql -h <HOST> -P 3306 -u tech0 -p gen12-mysql-pos < pos-app/backend/schema.sql
```

> `schema.sql` にはローカル検証用の初期データ（`STAFF001/password` など）が含まれます。運用環境では必ず変更してください。

## Backend 起動

```bash
cd pos-app/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Frontend 起動

```bash
cd pos-app/frontend
npm install
npm run dev
```

ブラウザで `http://localhost:3000` を開きます。

## 実装済み要点

- JWT Cookie（HttpOnly / SameSite=Strict、本番時Secure）認証
- RBAC（`ADMIN`専用API）
- SQLAlchemy利用によるDBアクセス（SQLインジェクション対策）
- 会員未存在時はエラーにせず「該当会員なし」で継続
- 会員ID入力時の値引き再適用（見積API）
- 購入確定時のサーバー再計算＆改ざん検知（合計不一致で400）
- 税率テーブル参照 + 1時間TTLキャッシュ
- 購入確定時の単価スナップショット保存（base/discounted/final）

## テスト

```bash
cd pos-app/backend
pytest -q
```

主要業務フロー（ログイン、会員照合、値引き再適用、金額改ざん検知）を自動テストしています。
