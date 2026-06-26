"""专业查询 API"""
from flask import Blueprint, request, jsonify
from models.database import query

majors_bp = Blueprint("majors", __name__)


@majors_bp.route("/api/majors")
def list_majors():
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 30, type=int)
    discipline = request.args.get("discipline", "")
    search = request.args.get("search", "").strip()
    
    conditions = ["1=1"]
    params = []
    
    if discipline:
        conditions.append("discipline = ?")
        params.append(discipline)
    if search:
        conditions.append("(name LIKE ? OR category LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    
    where = " AND ".join(conditions)
    
    total_row = query(f"SELECT COUNT(*) as c FROM majors WHERE {where}", params, one=True)
    total = total_row["c"]
    
    offset = (page - 1) * page_size
    rows = query(f"""
        SELECT * FROM majors WHERE {where}
        ORDER BY code LIMIT ? OFFSET ?
    """, params + [page_size, offset])
    
    return jsonify({
        "code": 0,
        "data": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@majors_bp.route("/api/majors/search")
def search_majors():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"code": 0, "data": [], "total": 0})
    
    rows = query("""
        SELECT * FROM majors
        WHERE name LIKE ? OR category LIKE ? OR discipline LIKE ?
        ORDER BY code LIMIT 50
    """, (f"%{q}%", f"%{q}%", f"%{q}%"))
    
    return jsonify({"code": 0, "data": [dict(r) for r in rows], "total": len(rows)})


@majors_bp.route("/api/majors/<int:major_id>")
def major_detail(major_id):
    row = query("SELECT * FROM majors WHERE id = ?", (major_id,), one=True)
    if not row:
        return jsonify({"code": 404, "message": "专业不存在"}), 404
    return jsonify({"code": 0, "data": dict(row)})


@majors_bp.route("/api/majors/disciplines")
def list_disciplines():
    rows = query("SELECT DISTINCT discipline FROM majors ORDER BY discipline")
    return jsonify({"code": 0, "data": [r["discipline"] for r in rows]})


@majors_bp.route("/api/majors/hot")
def hot_majors():
    """热门专业：按录取数据中出现的频率排序"""
    rows = query("""
        SELECT m.id, m.name, m.discipline, m.category, m.degree_type,
               COUNT(a.id) as school_count
        FROM majors m
        LEFT JOIN admission_scores a ON a.major_name LIKE '%' || m.name || '%'
        GROUP BY m.id
        HAVING school_count > 0
        ORDER BY school_count DESC
        LIMIT 30
    """)
    return jsonify({"code": 0, "data": [dict(r) for r in rows]})
