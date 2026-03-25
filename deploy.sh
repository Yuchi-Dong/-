#!/bin/bash
# ══════════════════════════════════════════════════════════════════
# 锡林郭勒云盘 v2.0 部署脚本
# 用法：bash deploy.sh [dev|prod]
# ══════════════════════════════════════════════════════════════════
set -euo pipefail

ENV="${1:-dev}"
INSTALL_DIR="/opt/secftp"
VENV_DIR="$INSTALL_DIR/venv"
APP_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  锡林郭勒云盘 v2.0 部署脚本 [mode=$ENV]"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 检查依赖 ─────────────────────────────────────────
command -v python3 >/dev/null || { echo "错误：未找到 python3"; exit 1; }
command -v node    >/dev/null || { echo "错误：未找到 node.js"; exit 1; }
command -v npm     >/dev/null || { echo "错误：未找到 npm"; exit 1; }
command -v pg_isready >/dev/null || echo "警告：未找到 pg_isready，跳过 DB 检查"

# ── 生成密钥（如未设置）───────────────────────────────
if [ -z "${SECFTP_SECRET_KEY:-}" ]; then
  export SECFTP_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  echo "🔑 生成随机 SECRET_KEY（生产环境请写入 /etc/secftp/env）"
fi

# ── 构建前端 ─────────────────────────────────────────
echo ""
echo "▶ 构建前端..."
cd "$APP_DIR/frontend"
npm install --silent
npm run build
echo "  ✓ 前端构建完成 → $APP_DIR/static/"
cd "$APP_DIR"

# ── Python 虚拟环境 ───────────────────────────────────
echo ""
echo "▶ 安装 Python 依赖..."
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"
echo "  ✓ Python 依赖安装完成"

# ── 数据库初始化 ──────────────────────────────────────
echo ""
echo "▶ 初始化数据库 Schema..."
cd "$APP_DIR"
"$VENV_DIR/bin/python3" -c "
import sys; sys.path.insert(0, '.')
import config
from core.db import init_pool; init_pool()
from infra.models import init_db; init_db()
print('  ✓ 数据库初始化完成')
"

# ── 生成密钥对（首次部署）────────────────────────────
if [ ! -f "/etc/secftp/vendor_private.pem" ]; then
  echo ""
  echo "▶ 生成 RSA-4096 密钥对（文件加密用）..."
  mkdir -p /etc/secftp
  python3 -c "
from core.crypto.engine import KeyManager
priv, pub = KeyManager.generate_key_pair(4096)
with open('/etc/secftp/vendor_private.pem','wb') as f: f.write(priv)
with open('/etc/secftp/vendor_public.pem','wb') as f: f.write(pub)
print('  ✓ 密钥对已生成')
print('  ⚠ 请妥善保管 /etc/secftp/vendor_private.pem！')
print('  ⚠ 该文件丢失后所有加密文件将无法解密！')
"
  chmod 600 /etc/secftp/vendor_private.pem
fi

# ── systemd 服务（Linux）───────────────────────────────
if command -v systemctl &>/dev/null && [ "$ENV" = "prod" ]; then
  cat > /etc/systemd/system/secftp.service << EOF
[Unit]
Description=锡林郭勒云盘 v2.0
After=network.target postgresql.service

[Service]
User=secftp
WorkingDirectory=$APP_DIR
Environment=SECFTP_SECRET_KEY=${SECFTP_SECRET_KEY}
Environment=SECFTP_VENDOR_KEY_FILE=/etc/secftp/vendor_private.pem
Environment=SECFTP_VENDOR_PUBKEY_FILE=/etc/secftp/vendor_public.pem
Environment=FLASK_ENV=production
ExecStart=$VENV_DIR/bin/waitress-serve --host=127.0.0.1 --port=8080 --threads=8 app:create_app
Restart=on-failure
RestartSec=5s
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable secftp
  systemctl restart secftp
  echo "  ✓ systemd 服务已启动"
  echo "  查看日志: journalctl -u secftp -f"
else
  echo ""
  echo "▶ 启动开发服务器..."
  export SECFTP_VENDOR_KEY_FILE="/etc/secftp/vendor_private.pem"
  export SECFTP_VENDOR_PUBKEY_FILE="/etc/secftp/vendor_public.pem"
  "$VENV_DIR/bin/python3" -m waitress --host=0.0.0.0 --port=8080 --threads=4 \
    --call app:create_app &
  echo "  ✓ 服务已启动: http://localhost:8080"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  部署完成！"
echo "  默认账号: admin / Admin@2025!"
echo "  请登录后立即修改密码！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
