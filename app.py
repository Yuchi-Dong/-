# -*- coding: utf-8 -*-
"""
app.py — Flask 应用工厂 v2.0

架构：
  core/     基础能力（crypto, db, auth, storage）
  product/  业务功能（files, audit, dashboard, admin）
  platform/ 平台能力（license, branding）
  infra/    基础设施（models）
"""
import json, logging, os, sys, traceback
from flask import Flask, jsonify, redirect, request, session, g, abort

import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("app")


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="")

    # Flask 配置
    app.secret_key                        = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"]      = None  # 不限制（大文件分片上传）
    app.config["SESSION_COOKIE_SECURE"]   = config.SESSION_COOKIE_SECURE
    app.config["SESSION_COOKIE_HTTPONLY"] = config.SESSION_COOKIE_HTTPONLY
    app.config["SESSION_COOKIE_SAMESITE"] = config.SESSION_COOKIE_SAMESITE

    # 生产环境 SECRET_KEY 检测
    if config.SECRET_KEY_IS_RANDOM:
        log.warning("⚠ SECFTP_SECRET_KEY 未设置，使用随机密钥（重启后 JWT 全部失效）")
        if os.environ.get("FLASK_ENV") == "production":
            raise RuntimeError("生产环境必须设置 SECFTP_SECRET_KEY！")

    # 初始化各子系统
    _init_db()
    _init_crypto()
    _init_storage()
    _init_schema()
    _load_platform_config()

    # 注册蓝图
    _register_blueprints(app)

    # 注册中间件
    _register_middleware(app)

    # Rate Limiting
    _setup_rate_limiting(app)

    # 健康检查
    @app.route("/health")
    def health():
        from core.db import get_conn
        from core.crypto.key_service import is_encryption_available, can_decrypt
        import time
        t0 = time.perf_counter()
        db_ok, db_err = False, ""
        try:
            with get_conn() as conn:
                conn.execute("SELECT 1")
            db_ok = True
        except Exception as e:
            db_err = str(e)
        return jsonify({
            "status":      "ok" if db_ok else "error",
            "db":          "ok" if db_ok else db_err,
            "db_ms":       round((time.perf_counter()-t0)*1000, 1),
            "encryption":  "enabled" if is_encryption_available() else "disabled",
            "can_decrypt": can_decrypt(),
            "version":     "2.0",
        }), 200 if db_ok else 503

    # SPA Fallback（Vue Router history mode）
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def spa_fallback(path):
        # API 路由不走 SPA
        if path.startswith("api/") or path.startswith("file/") or \
           path in ("health", "webdav") or path.startswith("webdav/") or \
           path.startswith("s/") or path.startswith("avatar/"):
            abort(404)
        index = os.path.join(app.static_folder, "index.html")
        if os.path.isfile(index):
            return app.send_static_file("index.html")
        return jsonify({"error": "前端未构建，请运行 npm run build"}), 503

    # 后台调度器
    _start_scheduler()
    log.info("✅ 应用初始化完成")
    return app


def _init_db():
    from core.db import init_pool
    init_pool(min_conn=config.DB_POOL_MIN, max_conn=config.DB_POOL_MAX)


def _init_crypto():
    from core.crypto.key_service import init_key_service
    init_key_service()


def _init_storage():
    from core.storage import init_storage
    init_storage(config.FILE_ROOT)


def _init_schema():
    from infra.models import init_db
    init_db()


def _load_platform_config():
    try:
        from core.db import get_conn
        with get_conn() as conn:
            rows = conn.execute("SELECT key, value FROM system_config").fetchall()
        for row in rows:
            k, v = row["key"], row["value"]
            if k == "branding" and isinstance(v, dict):
                for attr, val in {
                    "SYSTEM_NAME": v.get("system_name"),
                    "SYSTEM_ORG":  v.get("system_org"),
                    "ALLOW_REGISTER": v.get("allow_register"),
                }.items():
                    if val is not None: setattr(config, attr, val)
    except Exception as e:
        log.debug(f"加载平台配置失败（首次部署可忽略）: {e}")


def _register_blueprints(app: Flask):
    # ── 认证（新 JWT API）─────────────────────────────
    from core.auth.api      import bp as auth_api_bp
    # ── 文件（新 REST API）───────────────────────────
    from product.files.api  import bp as files_api_bp
    # ── 仪表盘 API ───────────────────────────────────
    from product.dashboard.api import bp as dashboard_api_bp
    # ── 管理员 API ───────────────────────────────────
    from product.admin.api  import bp as admin_api_bp
    # ── 个人中心 API ─────────────────────────────────
    from core.auth.profile_api import bp as profile_api_bp
    # ── 公开链接访问 ─────────────────────────────────
    from product.sharing.public import bp as public_bp
    # ── 头像服务 ─────────────────────────────────────
    from core.auth.avatar   import bp as avatar_bp
    # ── WebDAV ───────────────────────────────────────
    from product.files.webdav_api import bp as webdav_bp
    # ── 品牌配置 API ─────────────────────────────────
    from platform.branding.routes  import bp as branding_bp
    from product.audit.file_access import bp as file_access_bp
    from platform.license.checker  import license_bp
    from infra.metrics             import bp as metrics_bp, init_metrics
    init_metrics(app)

    for bp in [
        auth_api_bp, files_api_bp, dashboard_api_bp,
        admin_api_bp, profile_api_bp, public_bp,
        avatar_bp, webdav_bp, branding_bp,
    ]:
        app.register_blueprint(bp)

    log.info(f"蓝图注册完成：{len(app.blueprints)} 个")


def _register_middleware(app: Flask):
    @app.after_request
    def security_headers(response):
        is_file = request.path.startswith(("/api/file/", "/avatar/"))
        for k, v in config.SECURITY_HEADERS.items():
            if k == "X-Frame-Options" and is_file:
                continue
            response.headers.setdefault(k, v)
        if is_file:
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response

    @app.errorhandler(404)
    def e404(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "接口不存在"}), 404
        return jsonify({"error": "Not Found"}), 404

    @app.errorhandler(429)
    def e429(e):
        return jsonify({"error": "请求过于频繁，请稍后重试"}), 429

    @app.errorhandler(500)
    def e500(e):
        log.error("500:\n" + traceback.format_exc())
        return jsonify({"error": "服务器内部错误，已记录日志"}), 500


def _setup_rate_limiting(app: Flask):
    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address
        Limiter(app=app, key_func=get_remote_address,
                default_limits=["600/minute"], storage_uri="memory://")
        log.info("Rate limiting 已启用")
    except ImportError:
        log.warning("flask-limiter 未安装")


def _start_scheduler():
    import threading, datetime, time, shutil
    def _job():
        while True:
            now    = datetime.datetime.now()
            target = now.replace(hour=3, minute=0, second=0, microsecond=0)
            if now >= target: target += datetime.timedelta(days=1)
            time.sleep((target - now).total_seconds())
            try:
                from core.db import get_conn
                ttl = getattr(config, "TRASH_TTL_DAYS", 30)
                with get_conn() as conn:
                    expired = conn.execute(
                        "SELECT id, trash_path FROM trash_items "
                        "WHERE deleted_at < NOW() - INTERVAL '%s days'", (ttl,)
                    ).fetchall()
                    for row in expired:
                        tp = row.get("trash_path","")
                        if tp and os.path.isfile(tp): os.remove(tp)
                        elif tp and os.path.isdir(tp): shutil.rmtree(tp, ignore_errors=True)
                    if expired:
                        conn.execute("DELETE FROM trash_items WHERE id=ANY(%s)", ([r["id"] for r in expired],))
                        log.info(f"回收站清理: {len(expired)} 条")
            except Exception as ex:
                log.warning(f"回收站清理失败: {ex}")
    threading.Thread(target=_job, daemon=True, name="trash-cleanup").start()


if __name__ == "__main__":
    app = create_app()
    app.run(host=config.WEB_HOST, port=config.WEB_PORT, debug=False)
