"""高校查询 API"""
from flask import Blueprint, request, jsonify
from models.database import query

schools_bp = Blueprint("schools", __name__)


@schools_bp.route("/api/schools")
def list_schools():
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    province = request.args.get("province", "")
    level = request.args.get("level", "")
    school_type = request.args.get("type", "")
    is_985 = request.args.get("is_985", type=int)
    is_211 = request.args.get("is_211", type=int)
    is_df = request.args.get("is_double_first_class", type=int)
    search = request.args.get("search", "").strip()
    
    conditions = ["1=1"]
    params = []
    
    if province:
        conditions.append("p.name = ?")
        params.append(province)
    if level:
        conditions.append("s.level = ?")
        params.append(level)
    if school_type:
        conditions.append("s.type = ?")
        params.append(school_type)
    if is_985 is not None:
        conditions.append("s.is_985 = ?")
        params.append(is_985)
    if is_211 is not None:
        conditions.append("s.is_211 = ?")
        params.append(is_211)
    if is_df is not None:
        conditions.append("s.is_double_first_class = ?")
        params.append(is_df)
    if search:
        conditions.append("s.name LIKE ?")
        params.append(f"%{search}%")
    
    where = " AND ".join(conditions)
    
    # 总数
    total_row = query(f"SELECT COUNT(*) as c FROM schools s LEFT JOIN provinces p ON s.province_id=p.id WHERE {where}", params, one=True)
    total = total_row["c"]
    
    # 分页数据
    offset = (page - 1) * page_size
    rows = query(f"""
        SELECT s.*, p.name as province_name
        FROM schools s
        LEFT JOIN provinces p ON s.province_id = p.id
        WHERE {where}
        ORDER BY s.is_985 DESC, s.is_211 DESC, s.is_double_first_class DESC, s.name
        LIMIT ? OFFSET ?
    """, params + [page_size, offset])
    
    return jsonify({
        "code": 0,
        "data": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@schools_bp.route("/api/schools/search")
def search_schools():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"code": 0, "data": [], "total": 0})
    
    rows = query("""
        SELECT s.*, p.name as province_name
        FROM schools s
        LEFT JOIN provinces p ON s.province_id = p.id
        WHERE s.name LIKE ? OR s.city LIKE ? OR s.description LIKE ?
        ORDER BY s.is_985 DESC, s.is_211 DESC, s.is_double_first_class DESC
        LIMIT 30
    """, (f"%{q}%", f"%{q}%", f"%{q}%"))
    
    return jsonify({
        "code": 0,
        "data": [dict(r) for r in rows],
        "total": len(rows),
    })


@schools_bp.route("/api/schools/<int:school_id>/score-trend")
def school_score_trend(school_id):
    """高校分数线趋势"""
    province = request.args.get("province", "")
    category = request.args.get("category", "理科")
    
    conditions = ["school_id = ?", "source = 'gaokao.cn'"]
    params = [school_id]
    if province:
        conditions.append("province_id = (SELECT id FROM provinces WHERE name = ?)")
        params.append(province)
    if category:
        conditions.append("category = ?")
        params.append(category)
    
    where = " AND ".join(conditions)
    rows = query(f"""
        SELECT year, category, batch, MIN(min_score) as min_s, AVG(min_score) as avg_s, COUNT(*) as cnt
        FROM admission_scores WHERE {where}
        GROUP BY year, batch ORDER BY year, batch
    """, params)
    return jsonify({"code": 0, "data": [dict(r) for r in rows]})


@schools_bp.route("/api/schools/ranking")
def school_ranking():
    """院校排行"""
    rank_by = request.args.get("by", "ruanke")
    field = f"rank_{rank_by}"
    
    rows = query(f"""
        SELECT id, name, province_id, city, level, type, is_985, is_211, is_double_first_class,
               rank_ruanke, rank_alumni, rank_qs, phd_count, master_count
        FROM schools WHERE {field} IS NOT NULL AND {field} != ''
        ORDER BY CAST({field} AS INTEGER) LIMIT 50
    """)
    
    prov_map = {r["id"]: r["name"] for r in query("SELECT id, name FROM provinces")}
    result = []
    for r in rows:
        d = dict(r)
        d["province_name"] = prov_map.get(r["province_id"], "")
        result.append(d)
    
    return jsonify({"code": 0, "data": result})


@schools_bp.route("/api/schools/<int:school_id>")
def school_detail(school_id):
    row = query("""
        SELECT s.*, p.name as province_name
        FROM schools s
        LEFT JOIN provinces p ON s.province_id = p.id
        WHERE s.id = ?
    """, (school_id,), one=True)
    
    if not row:
        return jsonify({"code": 404, "message": "高校不存在"}), 404
    
    return jsonify({"code": 0, "data": dict(row)})


@schools_bp.route("/api/schools/stats")
def school_stats():
    """高校统计：按省份、类型、层次"""
    by_province = query("""
        SELECT p.name, COUNT(*) as count
        FROM schools s JOIN provinces p ON s.province_id = p.id
        GROUP BY s.province_id ORDER BY count DESC
    """)
    
    by_type = query("SELECT type, COUNT(*) as count FROM schools GROUP BY type ORDER BY count DESC")
    
    by_level = query("SELECT level, COUNT(*) as count FROM schools GROUP BY level ORDER BY count DESC")
    
    n_985 = query("SELECT COUNT(*) as c FROM schools WHERE is_985=1", one=True)["c"]
    n_211 = query("SELECT COUNT(*) as c FROM schools WHERE is_211=1", one=True)["c"]
    n_df = query("SELECT COUNT(*) as c FROM schools WHERE is_double_first_class=1", one=True)["c"]
    
    return jsonify({
        "code": 0,
        "data": {
            "by_province": [dict(r) for r in by_province],
            "by_type": [dict(r) for r in by_type],
            "by_level": [dict(r) for r in by_level],
            "count_985": n_985,
            "count_211": n_211,
            "count_double_first_class": n_df,
        }
    })


@schools_bp.route("/api/schools/compare")
def compare_schools():
    ids = request.args.get("ids", "")
    if not ids:
        return jsonify({"code": 0, "data": []})
    
    id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()][:5]
    placeholders = ",".join("?" * len(id_list))
    
    rows = query(f"""
        SELECT s.*, p.name as province_name
        FROM schools s LEFT JOIN provinces p ON s.province_id = p.id
        WHERE s.id IN ({placeholders})
    """, id_list)
    
    return jsonify({"code": 0, "data": [dict(r) for r in rows]})
