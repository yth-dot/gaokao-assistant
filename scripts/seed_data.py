"""数据初始化 - 使用 DeepSeek API 生成高校和专业数据"""
import json
import time
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL_FAST
from models.database import init_db, execute, executemany, query
import requests

PROVINCES = [
    ("北京", "110000"), ("天津", "120000"), ("河北", "130000"), ("山西", "140000"),
    ("内蒙古", "150000"), ("辽宁", "210000"), ("吉林", "220000"), ("黑龙江", "230000"),
    ("上海", "310000"), ("江苏", "320000"), ("浙江", "330000"), ("安徽", "340000"),
    ("福建", "350000"), ("江西", "360000"), ("山东", "370000"), ("河南", "410000"),
    ("湖北", "420000"), ("湖南", "430000"), ("广东", "440000"), ("广西", "450000"),
    ("海南", "460000"), ("重庆", "500000"), ("四川", "510000"), ("贵州", "520000"),
    ("云南", "530000"), ("西藏", "540000"), ("陕西", "610000"), ("甘肃", "620000"),
    ("青海", "630000"), ("宁夏", "640000"), ("新疆", "650000"),
]

# 985高校完整名单
SCHOOLS_985 = {
    "北京大学", "清华大学", "中国人民大学", "北京师范大学", "北京航空航天大学",
    "北京理工大学", "中国农业大学", "中央民族大学", "南开大学", "天津大学",
    "大连理工大学", "东北大学", "吉林大学", "哈尔滨工业大学", "复旦大学",
    "同济大学", "上海交通大学", "华东师范大学", "南京大学", "东南大学",
    "浙江大学", "中国科学技术大学", "厦门大学", "山东大学", "中国海洋大学",
    "武汉大学", "华中科技大学", "湖南大学", "中南大学", "国防科技大学",
    "中山大学", "华南理工大学", "四川大学", "电子科技大学", "重庆大学",
    "西安交通大学", "西北工业大学", "西北农林科技大学", "兰州大学",
}

# 211高校（包含985）
SCHOOLS_211 = SCHOOLS_985 | {
    "北京交通大学", "北京工业大学", "北京科技大学", "北京化工大学", "北京邮电大学",
    "北京林业大学", "北京中医药大学", "北京外国语大学", "中国传媒大学",
    "中央财经大学", "对外经济贸易大学", "北京体育大学", "中国政法大学",
    "华北电力大学", "中国矿业大学(北京)", "中国石油大学(北京)", "中国地质大学(北京)",
    "河北工业大学", "太原理工大学", "内蒙古大学", "辽宁大学", "大连海事大学",
    "延边大学", "东北师范大学", "哈尔滨工程大学", "东北农业大学", "东北林业大学",
    "华东理工大学", "东华大学", "上海外国语大学", "上海财经大学", "上海大学",
    "南京航空航天大学", "南京理工大学", "中国矿业大学", "河海大学",
    "江南大学", "南京农业大学", "中国药科大学", "南京师范大学",
    "苏州大学", "安徽大学", "合肥工业大学", "福州大学",
    "南昌大学", "郑州大学", "武汉理工大学", "华中农业大学",
    "华中师范大学", "中南财经政法大学", "中国地质大学(武汉)",
    "湖南师范大学", "暨南大学", "华南师范大学", "广西大学",
    "海南大学", "西南交通大学", "四川农业大学", "西南大学",
    "西南财经大学", "贵州大学", "云南大学", "西藏大学",
    "西北大学", "西安电子科技大学", "长安大学", "陕西师范大学",
    "青海大学", "宁夏大学", "新疆大学", "石河子大学",
    "第二军医大学", "第四军医大学",
}

# 双一流（第二轮147所）
SCHOOLS_DF = {
    "北京大学", "清华大学", "中国人民大学", "北京师范大学", "北京航空航天大学",
    "北京理工大学", "中国农业大学", "中央民族大学", "南开大学", "天津大学",
    "大连理工大学", "东北大学", "吉林大学", "哈尔滨工业大学", "复旦大学",
    "同济大学", "上海交通大学", "华东师范大学", "南京大学", "东南大学",
    "浙江大学", "中国科学技术大学", "厦门大学", "山东大学", "中国海洋大学",
    "武汉大学", "华中科技大学", "湖南大学", "中南大学", "中山大学",
    "华南理工大学", "四川大学", "电子科技大学", "重庆大学", "西安交通大学",
    "西北工业大学", "西北农林科技大学", "兰州大学", "国防科技大学",
    "北京交通大学", "北京工业大学", "北京科技大学", "北京化工大学", "北京邮电大学",
    "北京林业大学", "北京协和医学院", "北京中医药大学", "北京外国语大学",
    "中国传媒大学", "中央财经大学", "对外经济贸易大学", "外交学院",
    "中国人民公安大学", "北京体育大学", "中国政法大学", "中国音乐学院",
    "中央美术学院", "中央戏剧学院", "中国科学院大学",
    "河北工业大学", "太原理工大学", "山西大学", "内蒙古大学", "辽宁大学",
    "大连海事大学", "延边大学", "东北师范大学", "哈尔滨工程大学",
    "东北农业大学", "东北林业大学", "华东理工大学", "东华大学",
    "上海外国语大学", "上海财经大学", "上海大学", "上海科技大学",
    "上海音乐学院", "上海体育学院", "南京航空航天大学", "南京理工大学",
    "中国矿业大学", "河海大学", "江南大学", "南京农业大学",
    "中国药科大学", "南京师范大学", "南京医科大学", "南京邮电大学",
    "南京信息工程大学", "南京林业大学", "苏州大学", "安徽大学",
    "合肥工业大学", "福州大学", "南昌大学", "郑州大学", "河南大学",
    "武汉理工大学", "华中农业大学", "华中师范大学", "中南财经政法大学",
    "湘潭大学", "湖南师范大学", "暨南大学", "华南师范大学",
    "华南农业大学", "广州医科大学", "南方科技大学", "广西大学",
    "海南大学", "西南交通大学", "四川农业大学", "西南大学",
    "西南财经大学", "成都理工大学", "西南石油大学", "电子科技大学(沙河)",
    "贵州大学", "云南大学", "西藏大学", "西北大学", "西安电子科技大学",
    "长安大学", "陕西师范大学", "青海大学", "宁夏大学", "新疆大学",
    "石河子大学", "中国石油大学(北京)", "中国地质大学(北京)",
    "中国矿业大学(北京)", "华北电力大学", "南方医科大学", "空军军医大学",
    "海军军医大学", "南京航空航天大学", "南京理工大学",
}


def deepseek_chat(messages, temperature=0.3, max_tokens=4000):
    """调用 DeepSeek API, 处理推理模型的 reasoning_content"""
    resp = requests.post(
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": DEEPSEEK_MODEL_FAST,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=180,
    )
    if resp.status_code != 200:
        print(f"  ❌ API Error: {resp.status_code} {resp.text[:200]}")
        return None
    
    data = resp.json()
    msg = data["choices"][0]["message"]
    content = msg.get("content", "") or ""
    reasoning = msg.get("reasoning_content", "") or ""
    
    # 推理模型可能把内容放在 reasoning_content 中
    text = content + reasoning
    return text


def extract_json_array(text):
    """从文本中提取JSON数组"""
    # 先尝试直接解析整个文本
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 尝试找到最后的JSON数组
    # 查找所有 [...] 块
    arrays = []
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '[':
            if depth == 0:
                start = i
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0 and start >= 0:
                arrays.append(text[start:i+1])
    
    # 尝试解析每个数组（从大到小）
    for arr_str in sorted(arrays, key=len, reverse=True):
        try:
            return json.loads(arr_str)
        except json.JSONDecodeError:
            continue
    
    return None


def import_provinces():
    for name, code in PROVINCES:
        execute("INSERT OR IGNORE INTO provinces (name, code) VALUES (?, ?)", (name, code))
    print(f"✅ 省份: {len(PROVINCES)} 个")


def import_majors():
    print("📡 正在生成专业目录...")
    
    prompt = """请输出中国普通高等学校本科专业目录（2025年版）的完整JSON数组。

格式要求（严格JSON）：
[
  {"code": "010101", "name": "哲学", "category": "哲学类", "discipline": "哲学", "degree_type": "哲学"},
  {"code": "020301K", "name": "金融学", "category": "金融学类", "discipline": "经济学", "degree_type": "经济学"},
  ...
]

学科门类共13个：哲学、经济学、法学、教育学、文学、历史学、理学、工学、农学、医学、管理学、艺术学、交叉学科。
请尽可能完整输出所有核心专业（至少150个），确保数据真实。
输出必须是纯JSON数组，放在你的回答最末尾。"""
    
    text = deepseek_chat([{"role": "user", "content": prompt}], max_tokens=8000)
    if not text:
        print("  ❌ API调用失败")
        return 0
    
    majors = extract_json_array(text)
    if not majors:
        print(f"  ⚠️ 无法提取JSON，原文末尾: {text[-300:]}")
        return 0
    
    count = 0
    for m in majors:
        try:
            execute(
                "INSERT OR IGNORE INTO majors (code, name, category, discipline, degree_type) VALUES (?, ?, ?, ?, ?)",
                (m.get("code", ""), m.get("name", ""), m.get("category", ""),
                 m.get("discipline", ""), m.get("degree_type", ""))
            )
            count += 1
        except Exception:
            pass
    print(f"✅ 专业: {count} 个")
    return count


def import_schools():
    print("📡 正在生成高校数据...")
    
    province_map = {row["name"]: row["id"] for row in query("SELECT id, name FROM provinces")}
    all_schools = []
    
    # 分6批请求
    batch_size = 6
    province_list = [p[0] for p in PROVINCES]
    
    for i in range(0, len(province_list), batch_size):
        batch = province_list[i:i+batch_size]
        idx = i // batch_size + 1
        print(f"  批次 {idx}/6: {', '.join(batch[:3])}...")
        
        prompt = f"""列出以下省份的主要高等院校：
{', '.join(batch)}

每个省列出最重要的本科和专科高校（每省约12-18所，优先知名高校）。

返回严格JSON数组：
[
  {{"name": "清华大学", "province": "北京", "city": "北京市", "level": "本科", "type": "综合"}},
  ...
]

字段: name(全称), province, city, level(本科/专科), type(综合/理工/师范/医药/农林/财经/政法/语言/艺术/体育/民族)

注意：
- 返回纯JSON数组，放在回答末尾
- 不要包含is_985/is_211/is_double_first_class等字段（系统已有）
- 每个省至少12所"""
        
        text = deepseek_chat([{"role": "user", "content": prompt}], max_tokens=8000)
        if not text:
            print(f"    ❌ API失败")
            continue
        
        schools = extract_json_array(text)
        if not schools:
            print(f"    ⚠️ 无法提取JSON")
            continue
        
        all_schools.extend(schools)
        print(f"    ✅ {len(schools)} 所")
        time.sleep(0.5)
    
    # 导入数据库（含标签）
    count = 0
    for s in all_schools:
        try:
            pid = province_map.get(s.get("province", ""))
            if not pid:
                continue
            name = s.get("name", "")
            execute(
                """INSERT OR IGNORE INTO schools 
                   (name, province_id, city, level, type, is_985, is_211, is_double_first_class)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, pid, s.get("city", ""), s.get("level", ""),
                 s.get("type", ""),
                 1 if name in SCHOOLS_985 else 0,
                 1 if name in SCHOOLS_211 else 0,
                 1 if name in SCHOOLS_DF else 0)
            )
            count += 1
        except Exception:
            pass
    
    print(f"✅ 高校: {count} 所")
    return count


def add_descriptions():
    print("📡 正在补充高校简介...")
    rows = query("SELECT id, name FROM schools WHERE description IS NULL OR description = ''")
    
    if not rows:
        print("  无需补充")
        return
    
    # 分批处理，每批30所
    batch_list = [rows[i:i+30] for i in range(0, len(rows), 30)]
    
    for bidx, batch in enumerate(batch_list):
        names = [r["name"] for r in batch]
        prompt = f"""请为以下高校各写一个简短简介（20-40字），突出办学层次和特色优势学科：

{json.dumps(names, ensure_ascii=False)}

返回严格JSON对象，key为学校全称，value为简介。放在回答末尾。"""
        
        text = deepseek_chat([{"role": "user", "content": prompt}], max_tokens=4000)
        if not text:
            continue
        
        # 提取JSON对象
        obj = extract_json_object(text)
        if not obj:
            print(f"    ⚠️ 批次{bidx+1} 解析失败")
            continue
        
        cnt = 0
        for name, desc in obj.items():
            if isinstance(desc, str) and len(desc) > 5:
                execute("UPDATE schools SET description = ? WHERE name = ?", (desc, name))
                cnt += 1
        print(f"    ✅ 批次{bidx+1}: {cnt} 所")
        time.sleep(0.3)


def extract_json_object(text):
    """从文本中提取JSON对象"""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 查找 {...} 块
    objects = []
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start >= 0:
                objects.append(text[start:i+1])
    
    for obj_str in sorted(objects, key=len, reverse=True):
        try:
            return json.loads(obj_str)
        except json.JSONDecodeError:
            continue
    return None


def main():
    print("🚀 数据初始化\n")
    
    init_db()
    import_provinces()
    
    n_majors = import_majors()
    n_schools = import_schools()
    add_descriptions()
    
    final_s = query("SELECT COUNT(*) as c FROM schools", one=True)["c"]
    final_m = query("SELECT COUNT(*) as c FROM majors", one=True)["c"]
    
    print(f"\n📊 最终统计: 高校 {final_s} 所 | 专业 {final_m} 个 | 省份 31 个")
    print("🎉 完成!")


if __name__ == "__main__":
    main()
