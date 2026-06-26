"""Flask 应用入口"""
from flask import Flask, render_template
from config import SECRET_KEY, DEBUG

app = Flask(__name__)
app.secret_key = SECRET_KEY

# 注册路由
from routes.api_schools import schools_bp
from routes.api_majors import majors_bp
from routes.api_ai import ai_bp

app.register_blueprint(schools_bp)
app.register_blueprint(majors_bp)
app.register_blueprint(ai_bp)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    from models.database import query
    s = query("SELECT COUNT(*) as c FROM schools", one=True)["c"]
    m = query("SELECT COUNT(*) as c FROM majors", one=True)["c"]
    return {"status": "ok", "schools": s, "majors": m}


@app.route("/download")
def download_code():
    """提供代码包下载，绕过沙箱网络限制"""
    import tarfile, io, os
    
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        base = os.path.dirname(os.path.abspath(__file__))
        for root, dirs, files in os.walk(base):
            # 跳过不需要的
            if "__pycache__" in root or ".git" in root or ".edgeone" in root:
                continue
            for f in files:
                if f.endswith(".pyc") or f.endswith(".log"):
                    continue
                path = os.path.join(root, f)
                arcname = os.path.relpath(path, base)
                tar.add(path, arcname=arcname)
    
    buf.seek(0)
    from flask import send_file
    return send_file(buf, mimetype="application/gzip", as_attachment=True,
                     download_name="gaokao-assistant.tar.gz")


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 启动 http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)

