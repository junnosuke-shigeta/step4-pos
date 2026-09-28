# step4-pos

FastAPI + MySQL のバックエンドと Next.js のフロントエンドで構成された簡易 POS アプリです。第三者がクローンしてそのまま検証しやすいように、Docker 起動、手動起動、環境変数、テスト手順をまとめています。

## 構成

- Backend: `pos-app/backend`
- Frontend: `pos-app/frontend`
- DB 初期化 SQL: `pos-app/backend/schema.sql`

## 前提ソフトウェア

### Docker を使う場合

- Docker Engine / Docker Desktop
- Docker Compose (`docker compose`)

### Docker を使わない場合

- Python 3.12 推奨
- Node.js 20 推奨
- npm 10 以上推奨
- MySQL 8 系

## 開発用ログイン情報

`schema.sql` にはローカル検証用の seed データが含まれています。

- スタッフ: `STAFF001` / `password`
- 管理者: `ADMIN001` / `password`
- 会員: `MEM001`

> [!WARNING]
> これらは開発確認専用です。本番環境では seed データをそのまま使わず、パスワード・SECRET_KEY・DB パスワードを必ず変更してください。

## 環境変数

### Backend (`pos-app/backend/.env`)

`pos-app/backend/.env.example` をコピーして使います。

| 変数名 | 例 | 用途 |
| --- | --- | --- |
| `APP_ENV` | `development` | `production` のときは安全な設定が必須です |
| `SECRET_KEY` | `local-development-only-change-this-secret-key` | JWT 署名鍵。`production` では 32 文字以上の安全な値が必要です |
| `ACCESS_TOKEN_EXPIRE_HOURS` | `8` | ログイン cookie の有効時間 |
| `DATABASE_URL` | `mysql+pymysql://<user>:<password>@127.0.0.1:3306/gen12-mysql-pos?charset=utf8mb4` | SQLAlchemy 接続先。設定すると `DB_*` より優先されます |
| `DB_HOST` | `127.0.0.1` | MySQL ホスト |
| `DB_PORT` | `3306` | MySQL ポート |
| `DB_NAME` | `gen12-mysql-pos` | MySQL データベース名 |
| `DB_USER` | `tech0` | MySQL ユーザー |
| `DB_PASSWORD` | `tech0devpass` | MySQL パスワード |
| `CORS_ALLOW_ORIGINS` | `http://localhost:3000` | フロントエンドのオリジン |

`APP_ENV=production` のときに `SECRET_KEY` が弱い、または DB 接続設定が不足している場合、バックエンドは起動時に分かりやすいエラーで停止します。

### Frontend (`pos-app/frontend/.env.local`)

`pos-app/frontend/.env.local.example` をコピーして使います。

| 変数名 | 例 | 用途 |
| --- | --- | --- |
| `INTERNAL_API_BASE_URL` | `http://localhost:8000` | Next.js サーバーが backend にプロキシするときの接続先 |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | ブラウザから呼ぶ API のベース URL |

## Docker で起動する方法

ルートディレクトリで実行します。

```bash
docker compose up --build
```

起動後の URL:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

補足:

- MySQL は `docker-compose.yml` で起動し、初回起動時に `pos-app/backend/schema.sql` が自動実行されます。
- 既定では frontend は同一オリジンの `/api/...` を使い、Next.js が backend にプロキシします。Docker Compose では `INTERNAL_API_BASE_URL=http://backend:8000` を使用します。
- 別構成で直接 backend URL をブラウザへ埋め込みたい場合だけ、`NEXT_PUBLIC_API_BASE_URL` を `http://<ホスト名>:8000` のように設定してください。その値は frontend の build 時に取り込まれるため、変更した場合は frontend イメージを再 build してください。
- DB を seed から入れ直したい場合は、次でボリュームごと削除してください。

```bash
docker compose down -v
docker compose up --build
```

## Docker を使わない起動方法

### 1. MySQL を用意する

例:

```sql
CREATE DATABASE `gen12-mysql-pos`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER 'tech0'@'localhost' IDENTIFIED BY 'tech0devpass';
GRANT ALL PRIVILEGES ON `gen12-mysql-pos`.* TO 'tech0'@'localhost';
FLUSH PRIVILEGES;
```

### 2. DB を初期化する

```bash
mysql -h 127.0.0.1 -P 3306 -u tech0 -p gen12-mysql-pos < pos-app/backend/schema.sql
```

### 3. Backend を起動する

```bash
cd pos-app/backend
cp .env.example .env
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

起動確認:

```bash
curl http://localhost:8000/health
```

### 4. Frontend を起動する

別ターミナルで実行します。

```bash
cd pos-app/frontend
cp .env.local.example .env.local
npm ci
npm run dev
```

ブラウザで http://localhost:3000 を開いてログインしてください。

## テスト・検証コマンド

### Backend

```bash
cd pos-app/backend
. .venv/bin/activate
pytest -q
```

任意で MySQL スモークテストも実行できます。

```bash
export MYSQL_TEST_DATABASE_URL="mysql+pymysql://<user>:<password>@127.0.0.1:3306/gen12-mysql-pos?charset=utf8mb4"
pytest -q
```

### Frontend

```bash
cd pos-app/frontend
npm ci
npm run lint
npm run build
```

## 手動確認の流れ

1. `STAFF001 / password` でログイン
2. 会員 `MEM001` を照合
3. 商品コード `4901234567894` を追加
4. 見積金額が会員割引込みで再計算されることを確認
5. 購入確定する
6. 必要であれば `ADMIN001 / password` で管理者機能を確認する

## 開発時の注意

- 購入確定時はサーバー側で金額を再計算し、送信金額改ざんを拒否します。
- 購入明細保存の途中で例外が発生した場合は rollback され、購入データが中途半端に残らないようにしています。
