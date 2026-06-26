"""DeepSeek AI 辅助接口"""
from flask import Blueprint, request, jsonify, Response
from models.database import query
import requests
import json
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL_PRO

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/api/recommend")
def recommend():
    """智能推荐：根据分数和位次推荐高校"""
    score = request.args.get("score", type=float)
    rank = request.args.get("rank", type=int)
    province = request.args.get("province", "")
    category = request.args.get("category", "理科")
    
    year = request.args.get("year", 2024, type=int)
    
    # 科类映射：用户输入 → 数据库查询字段
    CATEGORY_MAP = {
        "理科": ["理科", "物理", "物理类"],
        "文科": ["文科", "历史", "历史类"],
        "综合": ["综合"],
        "物理": ["理科", "物理", "物理类"],
        "历史": ["文科", "历史", "历史类"],
        "艺术类": ["文科", "理科", "综合"],
        "体育类": ["文科", "理科", "综合"],
        "提前批": ["文科", "理科", "综合"],
    }
    db_categories = CATEGORY_MAP.get(category, [category])
    cat_placeholders = ",".join("?" * len(db_categories))
    cat_params = db_categories
    
    if not score or not province:
        return jsonify({"code": 400, "message": "请提供分数和省份"})
    
    # 获取省份ID
    province_row = query("SELECT id FROM provinces WHERE name = ?", (province,), one=True)
    if not province_row:
        return jsonify({"code": 400, "message": "省份不存在"})
    
    province_id = province_row["id"]
    
    # 获取批次线 — 根据科类智能过滤
    is_art = category in ('艺术类','艺术','美术','音乐','舞蹈')
    is_sport = category in ('体育类','体育')
    is_early = category in ('提前批','军校','公安')
    
    if is_art:
        batch_filter = "AND (batch LIKE '%艺术%')"
    elif is_sport:
        batch_filter = "AND (batch LIKE '%体育%')"
    elif is_early:
        batch_filter = "AND (batch LIKE '%提前%' OR batch LIKE '%军校%' OR batch LIKE '%公安%')"
    else:
        batch_filter = "AND (batch LIKE '%本科%' OR batch LIKE '%特殊类型%') AND batch NOT LIKE '%艺术%' AND batch NOT LIKE '%体育%'"
    
    batch_lines = query(f"""
        SELECT * FROM batch_lines
        WHERE province_id = ? AND category IN ({cat_placeholders}) AND year = ?
        {batch_filter}
        ORDER BY 
            CASE WHEN batch='本科批' THEN 0 WHEN batch LIKE '%一批%' THEN 1 
                 WHEN batch LIKE '%二批%' THEN 2 ELSE 3 END,
            score DESC
    """, [province_id] + cat_params + [year])
    
    # 去重：同名批次只保留第一条
    seen_batches = set()
    unique_lines = []
    for bl in batch_lines:
        key = bl["batch"] + "|" + bl["category"]
        if key not in seen_batches:
            seen_batches.add(key)
            unique_lines.append(bl)
    batch_lines = unique_lines
    
    if not batch_lines:
        batch_lines = query(f"""
            SELECT DISTINCT batch, category, MIN(score) as score, province_id, year
            FROM batch_lines
            WHERE province_id = ? AND category IN ({cat_placeholders})
            {batch_filter}
            GROUP BY batch, category
            ORDER BY year DESC, score DESC
            LIMIT 6
        """, [province_id] + cat_params)
    
    # 获取高校及分数线 — 根据科类过滤批次
    school_batch_filter = "AND (a.batch LIKE '%提前%' OR a.batch LIKE '%艺术%' OR a.batch LIKE '%体育%')" if (is_art or is_sport or is_early) else ""
    
    schools = query(f"""
        SELECT s.*, p.name as province_name,
               a.min_score, a.avg_score, a.min_rank, a.year, a.batch
        FROM schools s
        LEFT JOIN provinces p ON s.province_id = p.id
        LEFT JOIN admission_scores a ON s.id = a.school_id
        WHERE a.province_id = ? AND a.category IN ({cat_placeholders}) AND a.year = ?
        {school_batch_filter}
        ORDER BY s.is_985 DESC, s.is_211 DESC, a.min_score DESC
    """, [province_id] + cat_params + [year])
    
    # 分类：冲刺/稳妥/保底
    recommend_list = {"冲刺": [], "稳妥": [], "保底": []}
    seen = set()
    
    for row in schools:
        sid = row["id"]
        if sid in seen:
            continue
        seen.add(sid)
        
        min_score = row["min_score"] or 0
        gap = score - min_score
        
        # 冲刺：低30分以内 | 稳妥：±5分 | 保底：高5分以上
        if gap < -30:
            continue
        elif gap < -5:
            tag = "冲刺"
        elif -5 <= gap <= 5:
            tag = "稳妥"
        else:
            tag = "保底"
        
        recommend_list[tag].append({
            "id": row["id"],
            "name": row["name"],
            "province": row["province_name"],
            "city": row["city"],
            "level": row["level"],
            "type": row["type"],
            "is_985": row["is_985"],
            "is_211": row["is_211"],
            "is_double_first_class": row["is_double_first_class"],
            "min_score": row["min_score"],
            "gap": round(gap, 1),
            "year": row["year"],
        })
    
    # 排序限制
    for k in recommend_list:
        recommend_list[k] = sorted(recommend_list[k], key=lambda x: x["min_score"] or 0, reverse=True)[:20]
    
    # 查找一分一段数据
    rank_data = None
    if rank:
        cat_map = {"理科": "物理类", "文科": "历史类", "物理": "物理类", "历史": "历史类"}
        cat = cat_map.get(category, category)
        rank_row = query("""
            SELECT score, rank_position, school_name, school_score, source
            FROM one_point_tables
            WHERE province_id = ? AND year = ? AND category = ?
            AND rank_position >= ?
            ORDER BY rank_position ASC LIMIT 1
        """, (province_id, year, cat, rank), one=True)
        if rank_row:
            rank_data = dict(rank_row)
    
    return jsonify({
        "code": 0,
        "data": {
            "score": score,
            "rank": rank,
            "province": province,
            "category": category,
            "year": year,
            "batch_lines": [dict(r) for r in batch_lines],
            "recommendations": recommend_list,
            "total_matched": len(seen),
            "rank_info": rank_data,
        }
    })


@ai_bp.route("/api/ai/chat", methods=["POST"])
@ai_bp.route("/api/rank-to-score")
def rank_to_score():
    """位次换算：根据位次查对应分数和学校"""
    province = request.args.get("province", "")
    rank = request.args.get("rank", type=int)
    category = request.args.get("category", "物理类")
    year = request.args.get("year", 2025, type=int)
    
    if not province or not rank:
        return jsonify({"code": 400, "message": "请提供省份和位次"})
    
    cat_map = {"理科": "物理类", "文科": "历史类", "物理": "物理类", "历史": "历史类"}
    cat = cat_map.get(category, category)
    
    # 查找最接近的位次
    row = query("""
        SELECT score, rank_position, school_name, school_score, source
        FROM one_point_tables
        WHERE province_id = (SELECT id FROM provinces WHERE name=?)
        AND year = ? AND category = ?
        AND rank_position >= ?
        ORDER BY rank_position ASC LIMIT 3
    """, (province, year, cat, rank), one=True)
    
    if row:
        return jsonify({"code": 0, "data": dict(row)})
    
    return jsonify({"code": 404, "message": f"暂无{province}{year}年{cat}的位次数据，可尝试切换省份或年份"})


def ai_chat():
    """AI 对话"""
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"code": 400, "message": "请提供消息"})
    
    user_msg = data["message"]
    
    # 获取上下文数据
    school_count = query("SELECT COUNT(*) as c FROM schools", one=True)["c"]
    major_count = query("SELECT COUNT(*) as c FROM majors", one=True)["c"]
    
    system_prompt = f"""你是一个高考志愿填报助手，帮助家长和学生查询高校信息。
当前数据库有 {school_count} 所高校、{major_count} 个专业。
请根据用户问题给出专业、准确、通俗易懂的回答。用中文回复，适合家长阅读。"""
    
    try:
        resp = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": DEEPSEEK_MODEL_PRO,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                "max_tokens": 2000,
                "temperature": 0.7,
            },
            timeout=60,
        )
        
        if resp.status_code != 200:
            return jsonify({"code": 500, "message": "AI 服务异常"})
        
        result = resp.json()
        msg = result["choices"][0]["message"]
        content = msg.get("content", "") or msg.get("reasoning_content", "")
        
        return jsonify({"code": 0, "data": {"reply": content}})
    
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})
