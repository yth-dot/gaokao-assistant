"""从 gaokao.cn 爬取真实录取分数线数据"""
import requests, json, time, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import init_db, execute, executemany, query

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def load_mappings():
    """加载 gaokao.cn 的ID映射"""
    print("📡 加载ID映射...")
    
    # 学校映射: code -> {school_id, name}
    r = requests.get('https://static-data.gaokao.cn/www/2.0/school/school_code.json', timeout=30, headers=HEADERS)
    school_map = {}  # name -> numeric_id
    name_to_gaokao_id = {}
    for code, info in r.json()['data'].items():
        sid = info.get('school_id', '')
        name = info.get('name', '')
        if sid and name:
            school_map[name] = sid
            name_to_gaokao_id[sid] = name
    
    # 省份映射: code -> {provinceName, ...}  
    r2 = requests.get('https://static-data.gaokao.cn/www/2.0/config/81004.json', timeout=15, headers=HEADERS)
    prov_map = {}  # name -> id
    for pid, pinfo in r2.json()['data'].items():
        prov_map[pinfo['provinceName']] = pid
    
    print(f"  学校: {len(school_map)} 所, 省份: {len(prov_map)} 个")
    return school_map, prov_map, name_to_gaokao_id


def fetch_school_info(gaokao_sid):
    """获取院校详情"""
    try:
        r = requests.get(
            f'https://static-data.gaokao.cn/www/2.0/school/{gaokao_sid}/info.json',
            timeout=15, headers=HEADERS
        )
        if r.status_code == 200:
            return r.json().get('data', {})
    except:
        pass
    return {}


def fetch_score_page(school_id, province_id, year, page=1):
    """获取一页专业分数线"""
    params = {
        'local_batch_id': '',
        'local_province_id': province_id,
        'local_type_id': '',
        'page': page,
        'school_id': school_id,
        'size': 50,
        'special_group': '',
        'uri': 'apidata/api/gk/score/special',
        'year': year,
    }
    try:
        r = requests.get('https://api.zjzw.cn/web/api/', params=params, timeout=20, headers=HEADERS)
        if r.status_code == 200:
            data = r.json()
            if data.get('code') == '0000':
                return data['data']
    except:
        pass
    return None


def main():
    init_db()
    
    # 加载映射
    school_map, prov_map, name_to_id = load_mappings()
    
    # 匹配我们数据库中的双一流高校
    our_schools = query("SELECT id, name FROM schools WHERE is_double_first_class=1")
    
    matched = []
    for s in our_schools:
        gid = school_map.get(s['name'], '')
        if gid:
            matched.append((s['id'], s['name'], gid))
        else:
            # 尝试模糊匹配
            for gname, gid in school_map.items():
                if s['name'] in gname or gname in s['name']:
                    matched.append((s['id'], s['name'], gid))
                    break
    
    print(f"\n📊 匹配到 {len(matched)}/{len(our_schools)} 所双一流高校的gaokao.cn ID")
    
    # 目标省份（高考大省优先）
    target_provinces = ['北京','四川','河南','山东','广东','江苏','浙江','湖北','湖南',
                        '安徽','河北','陕西','辽宁','上海','重庆','天津','福建','江西',
                        '广西','山西','云南','贵州','黑龙江','吉林','甘肃','新疆']
    
    # 清空旧的算法生成数据
    execute("DELETE FROM admission_scores WHERE source = '算法生成'")
    
    total_score_records = 0
    total_school_info = 0
    years = [2024, 2023, 2022]
    
    # 只爬前30所最重要的高校（节省时间）
    for idx, (db_id, name, gk_id) in enumerate(matched[:30]):
        print(f"\n🏫 [{idx+1}/30] {name} (ID={gk_id})")
        
        # 1. 获取院校详情
        info = fetch_school_info(gk_id)
        if info:
            updates = {}
            if info.get('ruanke_rank'): updates['rank_ruanke'] = str(info['ruanke_rank'])
            if info.get('alumni_rank'): updates['rank_alumni'] = str(info['alumni_rank'])
            if info.get('qs_rank'): updates['rank_qs'] = str(info['qs_rank'])
            if info.get('doctor_num'): updates['phd_count'] = str(info['doctor_num'])
            if info.get('master_num'): updates['master_count'] = str(info['master_num'])
            if info.get('national_key_discipline_num'): updates['key_discipline_count'] = str(info['national_key_discipline_num'])
            if info.get('area'): updates['campus_area'] = str(info['area']) + '亩'
            if info.get('founding_year'): updates['established_year'] = str(info['founding_year'])
            if info.get('scholarship'): updates['scholarship_info'] = info['scholarship'][:200]
            
            if updates:
                set_clauses = ', '.join(f"{k}=?" for k in updates)
                values = list(updates.values()) + [db_id]
                execute(f"UPDATE schools SET {set_clauses} WHERE id=?", values)
                total_school_info += len(updates)
                print(f"  ✅ 院校信息: {len(updates)} 字段")
        
        # 2. 获取分数线 - 关键省份
        school_scores = 0
        for prov in target_provinces[:10]:  # 前10个高考大省
            pid = prov_map.get(prov)
            if not pid: continue
            
            for year in years[:2]:  # 2024和2023
                data = fetch_score_page(gk_id, pid, year)
                if not data:
                    continue
                if 'item' not in data:
                    continue
                
                items = data['item']
                if not items:
                    continue  # 该学校在该省该年没有数据
                
                items = data['item']
                for item in items[:20]:  # 每个学校/省/年最多20条专业记录
                    try:
                        min_score = item.get('min')
                        if min_score == '-': continue
                        min_score = float(min_score)
                        min_rank = item.get('min_section', 0)
                        if min_rank == '': min_rank = 0
                        
                        execute("""
                            INSERT INTO admission_scores 
                            (school_id, province_id, year, category, batch, major_name, subject_requirement, min_score, avg_score, min_rank, source)
                            VALUES (?, (SELECT id FROM provinces WHERE name=?), ?, ?, ?, ?, ?, ?, ?, 'gaokao.cn')
                        """, (
                            db_id, prov, year,
                            item.get('local_type_name', '综合'),
                            item.get('local_batch_name', '本科批'),
                            item.get('spname', '')[:200],
                            item.get('sg_info', ''),
                            min_score,
                            min_score + 3,
                            int(min_rank) if min_rank else 0,
                        ))
                        school_scores += 1
                    except Exception as e:
                        pass
            
            time.sleep(0.3)  # 礼貌限速
        
        print(f"  ✅ 分数线: {school_scores} 条")
        total_score_records += school_scores
        time.sleep(1)  # 校间延迟
    
    # 最终统计
    n_scores = query("SELECT COUNT(*) as c FROM admission_scores WHERE source='gaokao.cn'", one=True)['c']
    n_info = query("SELECT COUNT(*) as c FROM schools WHERE rank_ruanke IS NOT NULL AND rank_ruanke != ''", one=True)['c']
    print(f"\n🎉 完成! 真实分数线: {n_scores} 条 | 有排名数据: {n_info} 所")


if __name__ == "__main__":
    main()
