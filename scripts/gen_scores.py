"""分数线数据生成 - 使用 DeepSeek API 生成各省各高校历年录取分"""
import json, time, sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL_FAST
from models.database import init_db, execute, executemany, query
import requests

def deepseek_chat(prompt, max_tokens=4000):
    resp = requests.post(
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
        json={"model": DEEPSEEK_MODEL_FAST, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens, "temperature": 0.3},
        timeout=180,
    )
    if resp.status_code != 200:
        return ""
    msg = resp.json()["choices"][0]["message"]
    return (msg.get("content") or "") + (msg.get("reasoning_content") or "")


def generate_batch_lines():
    """生成各省份批次线"""
    print("📡 生成批次线...")
    
    provinces = [r["name"] for r in query("SELECT name FROM provinces ORDER BY id")]
    
    # 用DeepSeek生成2022-2024年各省批次线
    prompt = f"""请为以下31个省份生成2022-2024年高考本科批次线数据（理科/文科）。

返回严格JSON数组：
[
  {{"province":"北京","year":2024,"category":"理科","batch":"本科批","score":434}},
  ...
]

批次类型包括：本科批、特殊类型招生控制线（一本线参考）
各省批次名称按实际情况（如北京是"本科批"，四川是"本科一批"/"本科二批"）

注意：
- 分数要真实合理（参考历年实际数据）
- 每个省每年2条（理科+文科）×2批次 ≈ 每个省每年4条
- 3年×31省×4条 ≈ 约370条
- 直接返回纯JSON数组"""
    
    text = deepseek_chat(prompt, max_tokens=8000)
    if not text:
        print("  ❌ API失败，使用硬编码数据")
        return use_hardcoded_batch_lines()
    
    # 提取JSON
    import re
    arr = None
    # Try direct parse
    try:
        arr = json.loads(text)
    except:
        for m in re.finditer(r'\[[\s\S]*?\]', text):
            try:
                arr = json.loads(m.group())
                break
            except: continue
    
    if not arr or len(arr) < 50:
        print(f"  ⚠️ 生成数据不足({len(arr) if arr else 0}条)，使用硬编码")
        return use_hardcoded_batch_lines()
    
    prov_map = {r["name"]: r["id"] for r in query("SELECT id, name FROM provinces")}
    
    cnt = 0
    for item in arr:
        try:
            pid = prov_map.get(item.get("province", ""))
            if not pid: continue
            execute(
                "INSERT OR IGNORE INTO batch_lines (province_id, year, category, batch, score) VALUES (?,?,?,?,?)",
                (pid, item["year"], item["category"], item["batch"], item["score"])
            )
            cnt += 1
        except: pass
    
    print(f"  ✅ 批次线: {cnt} 条")
    return cnt


def use_hardcoded_batch_lines():
    """硬编码关键省份批次线（2024年参考）"""
    data = [
        # (省份, 年份, 科类, 批次, 分数)
        ("北京", 2024, "综合", "本科批", 434),
        ("北京", 2024, "综合", "特殊类型", 523),
        ("北京", 2023, "综合", "本科批", 448),
        ("北京", 2023, "综合", "特殊类型", 527),
        ("北京", 2022, "综合", "本科批", 425),
        ("北京", 2022, "综合", "特殊类型", 518),
        
        ("四川", 2024, "理科", "本科一批", 539),
        ("四川", 2024, "理科", "本科二批", 459),
        ("四川", 2024, "文科", "本科一批", 529),
        ("四川", 2024, "文科", "本科二批", 457),
        ("四川", 2023, "理科", "本科一批", 520),
        ("四川", 2023, "理科", "本科二批", 433),
        ("四川", 2023, "文科", "本科一批", 527),
        ("四川", 2023, "文科", "本科二批", 458),
        ("四川", 2022, "理科", "本科一批", 515),
        ("四川", 2022, "理科", "本科二批", 426),
        ("四川", 2022, "文科", "本科一批", 538),
        ("四川", 2022, "文科", "本科二批", 466),
        
        ("河南", 2024, "理科", "本科一批", 511),
        ("河南", 2024, "理科", "本科二批", 396),
        ("河南", 2024, "文科", "本科一批", 521),
        ("河南", 2024, "文科", "本科二批", 428),
        ("河南", 2023, "理科", "本科一批", 514),
        ("河南", 2023, "理科", "本科二批", 409),
        ("河南", 2023, "文科", "本科一批", 547),
        ("河南", 2023, "文科", "本科二批", 465),
        ("河南", 2022, "理科", "本科一批", 509),
        ("河南", 2022, "理科", "本科二批", 405),
        ("河南", 2022, "文科", "本科一批", 527),
        ("河南", 2022, "文科", "本科二批", 445),
        
        ("山东", 2024, "综合", "本科批", 444),
        ("山东", 2024, "综合", "特殊类型", 521),
        ("山东", 2023, "综合", "本科批", 443),
        ("山东", 2023, "综合", "特殊类型", 520),
        ("山东", 2022, "综合", "本科批", 437),
        ("山东", 2022, "综合", "特殊类型", 513),
        
        ("广东", 2024, "物理", "本科批", 442),
        ("广东", 2024, "历史", "本科批", 428),
        ("广东", 2024, "物理", "特殊类型", 532),
        ("广东", 2024, "历史", "特殊类型", 539),
        ("广东", 2023, "物理", "本科批", 439),
        ("广东", 2023, "历史", "本科批", 433),
        ("广东", 2023, "物理", "特殊类型", 539),
        ("广东", 2023, "历史", "特殊类型", 540),
        ("广东", 2022, "物理", "本科批", 445),
        ("广东", 2022, "历史", "本科批", 437),
        
        ("江苏", 2024, "物理", "本科批", 462),
        ("江苏", 2024, "历史", "本科批", 478),
        ("江苏", 2024, "物理", "特殊类型", 516),
        ("江苏", 2024, "历史", "特殊类型", 530),
        ("江苏", 2023, "物理", "本科批", 448),
        ("江苏", 2023, "历史", "本科批", 474),
        ("江苏", 2022, "物理", "本科批", 429),
        ("江苏", 2022, "历史", "本科批", 471),
        
        ("浙江", 2024, "综合", "本科批", 492),
        ("浙江", 2024, "综合", "特殊类型", 595),
        ("浙江", 2023, "综合", "本科批", 488),
        ("浙江", 2023, "综合", "特殊类型", 594),
        ("浙江", 2022, "综合", "本科批", 497),
        ("浙江", 2022, "综合", "特殊类型", 592),
        
        ("湖北", 2024, "物理", "本科批", 437),
        ("湖北", 2024, "历史", "本科批", 432),
        ("湖北", 2024, "物理", "特殊类型", 525),
        ("湖北", 2024, "历史", "特殊类型", 530),
        ("湖北", 2023, "物理", "本科批", 424),
        ("湖北", 2023, "历史", "本科批", 426),
        ("湖北", 2022, "物理", "本科批", 409),
        ("湖北", 2022, "历史", "本科批", 435),
        
        ("湖南", 2024, "物理", "本科批", 422),
        ("湖南", 2024, "历史", "本科批", 438),
        ("湖南", 2024, "物理", "特殊类型", 481),
        ("湖南", 2024, "历史", "特殊类型", 496),
        ("湖南", 2023, "物理", "本科批", 415),
        ("湖南", 2023, "历史", "本科批", 428),
        ("湖南", 2022, "物理", "本科批", 414),
        ("湖南", 2022, "历史", "本科批", 451),
        
        ("安徽", 2024, "物理", "本科批", 465),
        ("安徽", 2024, "历史", "本科批", 462),
        ("安徽", 2024, "物理", "特殊类型", 514),
        ("安徽", 2024, "历史", "特殊类型", 512),
        ("安徽", 2023, "理科", "本科一批", 482),
        ("安徽", 2023, "文科", "本科一批", 495),
        ("安徽", 2022, "理科", "本科一批", 491),
        ("安徽", 2022, "文科", "本科一批", 523),
        
        ("河北", 2024, "物理", "本科批", 448),
        ("河北", 2024, "历史", "本科批", 449),
        ("河北", 2024, "物理", "特殊类型", 506),
        ("河北", 2024, "历史", "特殊类型", 506),
        ("河北", 2023, "物理", "本科批", 439),
        ("河北", 2023, "历史", "本科批", 430),
        ("河北", 2022, "物理", "本科批", 430),
        ("河北", 2022, "历史", "本科批", 443),
        
        ("辽宁", 2024, "物理", "本科批", 368),
        ("辽宁", 2024, "历史", "本科批", 400),
        ("辽宁", 2024, "物理", "特殊类型", 510),
        ("辽宁", 2024, "历史", "特殊类型", 510),
        ("辽宁", 2023, "物理", "本科批", 360),
        ("辽宁", 2023, "历史", "本科批", 404),
        
        ("陕西", 2024, "理科", "本科一批", 475),
        ("陕西", 2024, "文科", "本科一批", 488),
        ("陕西", 2024, "理科", "本科二批", 372),
        ("陕西", 2024, "文科", "本科二批", 397),
        ("陕西", 2023, "理科", "本科一批", 443),
        ("陕西", 2023, "文科", "本科一批", 489),
        
        ("上海", 2024, "综合", "本科批", 403),
        ("上海", 2024, "综合", "特殊类型", 503),
        ("上海", 2023, "综合", "本科批", 405),
        ("上海", 2023, "综合", "特殊类型", 504),
        
        ("天津", 2024, "综合", "本科批", 475),
        ("天津", 2024, "综合", "特殊类型", 563),
        ("天津", 2023, "综合", "本科批", 472),
        ("天津", 2023, "综合", "特殊类型", 563),
        
        ("重庆", 2024, "物理", "本科批", 427),
        ("重庆", 2024, "历史", "本科批", 428),
        ("重庆", 2024, "物理", "特殊类型", 499),
        ("重庆", 2024, "历史", "特殊类型", 506),
    ]
    
    prov_map = {r["name"]: r["id"] for r in query("SELECT id, name FROM provinces")}
    cnt = 0
    for prov, year, cat, batch, score in data:
        pid = prov_map.get(prov)
        if not pid: continue
        execute(
            "INSERT OR IGNORE INTO batch_lines (province_id, year, category, batch, score) VALUES (?,?,?,?,?)",
            (pid, year, cat, batch, score)
        )
        cnt += 1
    
    print(f"  ✅ 批次线(硬编码): {cnt} 条")
    return cnt


def generate_admission_scores():
    """生成各高校在各省的录取分数线"""
    print("📡 生成高校录取分数线...")
    
    # 获取985和211高校
    top_schools = query("""
        SELECT id, name, province_id, is_985, is_211, is_double_first_class FROM schools 
        WHERE is_985=1 OR is_211=1 OR is_double_first_class=1
        ORDER BY is_985 DESC, is_211 DESC
    """)
    
    provinces = query("SELECT id, name FROM provinces ORDER BY id")
    
    # 策略：对每个重点高校，在几个主要省份生成分数线
    # 为加速，只对985/211在10个高考大省生成数据
    major_provinces = ["北京","四川","河南","山东","广东","江苏","浙江","湖北","湖南","安徽"]
    
    # 使用合理的分数范围（985高校比211高，热门省份比冷门高）
    # 基于学校层次生成合理分数
    
    # 直接使用算法生成，避免大量API调用
    year_range = [2022, 2023, 2024]
    
    score_data = []
    
    for school in top_schools[:120]:  # 限制120所重点高校
        sid = school["id"]
        
        # 确定学校分数段
        if school["is_985"]:
            base_score = random.randint(620, 690)  # 985高校
        elif school["is_211"]:
            base_score = random.randint(550, 640)  # 211高校
        else:
            base_score = random.randint(500, 580)  # 其他双一流
        
        # 学校所在地如果和招生省份相同，分数稍低
        school_prov = None
        for r in provinces:
            if r["id"] == school["province_id"]:
                school_prov = r["name"]
                break
        
        for prov in major_provinces:
            pid = next((r["id"] for r in provinces if r["name"] == prov), None)
            if not pid: continue
            
            # 本地高校在本地招生分数会低一些
            local_bonus = -10 if prov == school_prov else 0
            
            for yr in year_range:
                # 每年分数有微小波动
                year_adj = random.randint(-5, 5)
                
                for cat in ["理科", "文科"]:
                    # 文科通常比理科高或低取决于学校类型
                    cat_adj = random.randint(-10, 5) if cat == "文科" else 0
                    
                    min_score = base_score + local_bonus + year_adj + cat_adj
                    # 分数范围调整到合理区间
                    min_score = max(400, min(700, min_score))
                    avg_score = min_score + random.randint(3, 12)
                    max_score = avg_score + random.randint(2, 10)
                    min_rank = int((750 - min_score) * random.randint(800, 2000))
                    
                    score_data.append((sid, pid, yr, cat, "本科批", min_score, avg_score, max_score, min_rank, "算法生成"))
    
    # 批量插入
    if score_data:
        cnt = executemany(
            """INSERT OR IGNORE INTO admission_scores 
               (school_id, province_id, year, category, batch, min_score, avg_score, max_score, min_rank, source)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            score_data
        )
        print(f"  ✅ 录取分数线: {cnt} 条 ({len(top_schools[:120])} 校 × 10 省 × 3 年 × 2 科)")
    else:
        print("  无数据生成")


def main():
    init_db()
    
    # 清空旧数据
    execute("DELETE FROM batch_lines")
    execute("DELETE FROM admission_scores")
    
    # 1. 批次线
    n1 = generate_batch_lines()
    
    # 2. 录取分数线
    generate_admission_scores()
    
    # 统计
    bl = query("SELECT COUNT(*) as c FROM batch_lines", one=True)["c"]
    ascore = query("SELECT COUNT(*) as c FROM admission_scores", one=True)["c"]
    print(f"\n📊 分数线数据: 批次线 {bl} 条 | 录取分 {ascore} 条")


if __name__ == "__main__":
    main()
