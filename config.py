# -*- coding: utf-8 -*-
"""
config.py — 全局配置

优先级：环境变量 > 此文件默认值
所有敏感配置（密钥、密码）必须通过环境变量注入，此文件只保留非敏感默认值。
"""
import os
import secrets

# ── 基础安全 ─────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SECFTP_SECRET_KEY") or secrets.token_hex(32)
SECRET_KEY_IS_RANDOM = not bool(os.environ.get("SECFTP_SECRET_KEY"))

# ── 数据库 ───────────────────────────────────────────────────────
DB_HOST     = os.environ.get("DB_HOST",     "127.0.0.1")
DB_PORT     = int(os.environ.get("DB_PORT", "5432"))
DB_NAME     = os.environ.get("DB_NAME",     "secftp")
DB_USER     = os.environ.get("DB_USER",     "secftp")
DB_PASS     = os.environ.get("DB_PASS",     "secftp_pass")
DB_POOL_MIN = int(os.environ.get("DB_POOL_MIN", "2"))
DB_POOL_MAX = int(os.environ.get("DB_POOL_MAX", "20"))

# ── 文件存储 ─────────────────────────────────────────────────────
FILE_ROOT = os.environ.get("SECFTP_FILE_ROOT", r"C:\SecFTP\files")

# ── Web 服务 ─────────────────────────────────────────────────────
WEB_HOST = "0.0.0.0"
WEB_PORT = int(os.environ.get("SECFTP_PORT", "8080"))

# ── 会话安全 ─────────────────────────────────────────────────────
SESSION_TIMEOUT         = 3600
SESSION_COOKIE_SECURE   = os.environ.get("SECFTP_HTTPS", "false").lower() in ("1","true","yes")
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# ── 登录保护 ─────────────────────────────────────────────────────
MAX_LOGIN_FAIL  = 5
LOCKOUT_SECONDS = 300

# ── 上传限制 ─────────────────────────────────────────────────────
MAX_UPLOAD_MB       = 512
CHUNK_SIZE_MB       = 5
MAX_CHUNKED_FILE_GB = 100
AVATAR_MAX_KB       = 2048
AVATAR_SIZE         = 200

# ── 文件版本与回收站 ─────────────────────────────────────────────
MAX_FILE_VERSIONS = int(os.environ.get("SECFTP_MAX_VERSIONS", "10"))
TRASH_TTL_DAYS    = int(os.environ.get("SECFTP_TRASH_TTL_DAYS", "30"))

# ── 上传白名单 ───────────────────────────────────────────────────
UPLOAD_WHITELIST = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff",
    ".pdf", ".ofd",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".wps", ".et", ".dps",
    ".txt", ".md", ".csv", ".log", ".json", ".xml", ".yaml", ".ini",
    ".zip", ".rar", ".7z",
    ".mp4", ".mkv", ".avi", ".mov",
    ".mp3", ".wav", ".flac",
}

# ── 安全响应头 ────────────────────────────────────────────────────
SECURITY_HEADERS = {
    "X-Frame-Options":        "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy":        "strict-origin-when-cross-origin",
    "X-XSS-Protection":       "1; mode=block",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data:; "
        "connect-src 'self';"
    ),
}

# ── IP 管控 ──────────────────────────────────────────────────────
IP_BLACKLIST: set = set()

# ── 角色定义 ─────────────────────────────────────────────────────
ROLE_SUPER = 0
ROLE_DEPT  = 1
ROLE_USER  = 2
ROLE_NAMES = {0: "超级管理员", 1: "组织管理员", 2: "普通用户"}

# ── 组织层级 ─────────────────────────────────────────────────────
ORG_LEVEL_NAMES = {1: "委办局", 2: "业务科室", 3: "工作小组"}

# ── 告警 Webhook ─────────────────────────────────────────────────
ALERT_WECOM_WEBHOOK    = os.environ.get("ALERT_WECOM_WEBHOOK", "")
ALERT_DINGTALK_WEBHOOK = os.environ.get("ALERT_DINGTALK_WEBHOOK", "")

# ── OnlyOffice ────────────────────────────────────────────────────
ONLYOFFICE_ENABLED  = False
ONLYOFFICE_SERVER   = os.environ.get("ONLYOFFICE_SERVER", "")
ONLYOFFICE_JWT_KEY  = os.environ.get("ONLYOFFICE_JWT_KEY", "")
SECFTP_PUBLIC_URL   = os.environ.get("SECFTP_PUBLIC_URL", "")

# ── 系统名称（默认，可在 DB system_config 覆盖）──────────────────
SYSTEM_NAME    = os.environ.get("SECFTP_SYSTEM_NAME", "锡林郭勒云盘")
SYSTEM_NAME_EN = "Xilingol Cloud Drive"
SYSTEM_SHORT   = os.environ.get("SECFTP_SYSTEM_SHORT", "锡林郭勒云盘")
SYSTEM_ORG     = os.environ.get("SECFTP_SYSTEM_ORG", "锡林郭勒盟行政公署")

# ── 加密配置 ─────────────────────────────────────────────────────
# 密钥路径通过环境变量配置，此处只做开关
ENCRYPTION_ENABLED = os.environ.get("SECFTP_ENCRYPTION", "true").lower() != "false"

# ── LDAP ─────────────────────────────────────────────────────────
LDAP_ENABLED           = False
LDAP_SERVER            = os.environ.get("LDAP_SERVER", "")
LDAP_PORT              = int(os.environ.get("LDAP_PORT", "389"))
LDAP_USE_SSL           = os.environ.get("LDAP_USE_SSL", "false").lower() in ("1","true")
LDAP_BIND_DN           = os.environ.get("LDAP_BIND_DN", "")
LDAP_BIND_PASSWORD     = os.environ.get("LDAP_BIND_PASSWORD", "")
LDAP_BASE_DN           = os.environ.get("LDAP_BASE_DN", "")
LDAP_USER_FILTER       = os.environ.get("LDAP_USER_FILTER", "(sAMAccountName={username})")
LDAP_ATTR_USERNAME     = "sAMAccountName"
LDAP_ATTR_DISPLAY_NAME = "displayName"
LDAP_ATTR_EMAIL        = "mail"
LDAP_ATTR_PHONE        = "telephoneNumber"
LDAP_ATTR_DEPARTMENT   = "department"
LDAP_DEFAULT_ROLE      = 2
LDAP_DEFAULT_QUOTA_MB  = 1048576

# ── 存储后端 ─────────────────────────────────────────────────────
STORAGE_BACKEND  = os.environ.get("STORAGE_BACKEND", "local")
MINIO_ENDPOINT   = os.environ.get("MINIO_ENDPOINT",   "127.0.0.1:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET     = os.environ.get("MINIO_BUCKET",     "secftp-files")
MINIO_SECURE     = os.environ.get("MINIO_SECURE",     "false").lower() in ("1","true")

# ── 注册申请 ─────────────────────────────────────────────────────
ALLOW_REGISTER = False
