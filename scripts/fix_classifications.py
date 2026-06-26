"""完全修正高校分类 - 基于教育部第二轮双一流官方名单"""
import json, time, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import init_db, execute, query

# ====== 985高校 39所（全部也是211+双一流）======
SCHOOLS_985 = {
    "北京大学","中国人民大学","清华大学","北京航空航天大学","北京理工大学",
    "中国农业大学","北京师范大学","中央民族大学","南开大学","天津大学",
    "大连理工大学","东北大学","吉林大学","哈尔滨工业大学","复旦大学",
    "同济大学","上海交通大学","华东师范大学","南京大学","东南大学",
    "浙江大学","中国科学技术大学","厦门大学","山东大学","中国海洋大学",
    "武汉大学","华中科技大学","湖南大学","中南大学","中山大学",
    "华南理工大学","四川大学","电子科技大学","重庆大学","西安交通大学",
    "西北工业大学","西北农林科技大学","兰州大学","国防科技大学",
}

# ====== 非985的211高校 73所（全部也是双一流）======
SCHOOLS_211 = {
    "北京交通大学","北京工业大学","北京科技大学","北京化工大学","北京邮电大学",
    "北京林业大学","北京中医药大学","北京外国语大学","中国传媒大学",
    "中央财经大学","对外经济贸易大学","北京体育大学","中国政法大学",
    "华北电力大学","中国矿业大学(北京)","中国石油大学(北京)","中国地质大学(北京)",
    "河北工业大学","太原理工大学","内蒙古大学","辽宁大学","大连海事大学",
    "延边大学","东北师范大学","哈尔滨工程大学","东北农业大学","东北林业大学",
    "华东理工大学","东华大学","上海外国语大学","上海财经大学","上海大学",
    "南京航空航天大学","南京理工大学","中国矿业大学","河海大学",
    "江南大学","南京农业大学","中国药科大学","南京师范大学",
    "苏州大学","安徽大学","合肥工业大学","福州大学",
    "南昌大学","郑州大学","武汉理工大学","华中农业大学",
    "华中师范大学","中南财经政法大学","中国地质大学(武汉)",
    "湖南师范大学","暨南大学","华南师范大学","广西大学",
    "海南大学","西南交通大学","四川农业大学","西南大学",
    "西南财经大学","贵州大学","云南大学","西藏大学",
    "西北大学","西安电子科技大学","长安大学","陕西师范大学",
    "青海大学","宁夏大学","新疆大学","石河子大学",
    "第二军医大学(海军军医大学)","第四军医大学(空军军医大学)",
}

# ====== 非211双一流高校 35所 ======
SCHOOLS_DF_ONLY = {
    # 首轮28所非211双一流：
    "北京协和医学院","中国科学院大学","外交学院","中国人民公安大学",
    "中国音乐学院","中央美术学院","中央戏剧学院",
    "首都师范大学",
    "天津工业大学","天津中医药大学",
    "上海海洋大学","上海中医药大学","上海音乐学院","上海体育大学",
    "南京林业大学","南京信息工程大学","南京邮电大学","南京医科大学",
    "中国美术学院",
    "河南大学",
    "广州中医药大学","南京中医药大学",
    "成都理工大学","西南石油大学","成都中医药大学",
    "宁波大学",
    "南方医科大学",
    # 第二轮新增：
    "山西大学","湘潭大学","华南农业大学","广州医科大学",
    "南方科技大学","上海科技大学","南京医科大学",
}

# 211高校全量 = 985 + 纯211
ALL_211 = SCHOOLS_985 | SCHOOLS_211

# 双一流全量 = 211 + 非211双一流
ALL_DF = ALL_211 | SCHOOLS_DF_ONLY

print(f"985: {len(SCHOOLS_985)} 所")
print(f"非985的211: {len(SCHOOLS_211)} 所")
print(f"非211双一流: {len(SCHOOLS_DF_ONLY)} 所")
print(f"双一流总计: {len(ALL_DF)} 所")
print(f"双一流集合内高校数: {len(ALL_DF)}（目标147，偏差{147-len(ALL_DF)}）")


def fix_all_classifications():
    """修正所有高校的分类标签"""
    init_db()
    
    # 1. 先重置所有标签
    execute("UPDATE schools SET is_985=0, is_211=0, is_double_first_class=0")
    
    # 2. 逐校匹配修正
    fixed_985 = 0
    fixed_211 = 0
    fixed_df = 0
    
    for name in SCHOOLS_985:
        r = execute("UPDATE schools SET is_985=1, is_211=1, is_double_first_class=1 WHERE name LIKE ?", (f"%{name}%",))
        if r > 0:
            fixed_985 += r
    
    for name in SCHOOLS_211:
        r = execute("UPDATE schools SET is_211=1, is_double_first_class=1 WHERE name LIKE ? AND is_985=0", (f"%{name}%",))
        if r > 0:
            fixed_211 += r
    
    for name in SCHOOLS_DF_ONLY:
        r = execute("UPDATE schools SET is_double_first_class=1 WHERE name LIKE ?", (f"%{name}%",))
        if r > 0:
            fixed_df += r
    
    # 3. 特殊处理：军医大学等名称变体
    execute("UPDATE schools SET is_211=1, is_double_first_class=1 WHERE (name LIKE '%海军军医%' OR name LIKE '%第二军医%') AND is_985=0")
    execute("UPDATE schools SET is_211=1, is_double_first_class=1 WHERE (name LIKE '%空军军医%' OR name LIKE '%第四军医%') AND is_985=0")
    # 上海体育学院已更名上海体育大学
    execute("UPDATE schools SET is_double_first_class=1 WHERE name LIKE '%上海体育%'")
    
    # 4. 统计结果
    n985 = query("SELECT COUNT(*) as c FROM schools WHERE is_985=1", one=True)["c"]
    n211 = query("SELECT COUNT(*) as c FROM schools WHERE is_211=1", one=True)["c"]
    ndf = query("SELECT COUNT(*) as c FROM schools WHERE is_double_first_class=1", one=True)["c"]
    total = query("SELECT COUNT(*) as c FROM schools", one=True)["c"]
    
    print(f"\n修正结果: 总计 {total} 所高校")
    print(f"  985: {n985} 所 (应有39)")
    print(f"  211: {n211} 所 (应有112)")
    print(f"  双一流: {ndf} 所 (应有147)")
    
    # 5. 检查关键高校
    checks = ["河南大学","郑州大学","山西大学","湘潭大学","南方科技大学","上海科技大学"]
    for name in checks:
        r = query("SELECT name, is_985, is_211, is_double_first_class FROM schools WHERE name LIKE ?", (f"%{name}%",), one=True)
        if r:
            print(f"  ✅ {r['name']}: 985={r['is_985']} 211={r['is_211']} 双一流={r['is_double_first_class']}")
        else:
            print(f"  ❌ {name}: 不在数据库中!")
    
    # 6. 列出未匹配的双一流高校（数据库中可能缺失的）
    all_names = {r["name"] for r in query("SELECT name FROM schools")}
    missing_df = []
    for name in ALL_DF:
        found = False
        for db_name in all_names:
            if name in db_name or db_name in name:
                found = True
                break
        if not found:
            missing_df.append(name)
    
    if missing_df:
        print(f"\n⚠️ 数据库中可能缺失的146所双一流高校:")
        for n in sorted(missing_df):
            print(f"    - {n}")
    
    return n985, n211, ndf


if __name__ == "__main__":
    fix_all_classifications()
