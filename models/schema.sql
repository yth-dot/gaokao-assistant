-- 高考志愿填报查询网站 数据库 Schema
-- SQLite 3

-- 省份表
CREATE TABLE IF NOT EXISTS provinces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(20) NOT NULL UNIQUE,
    code VARCHAR(6) NOT NULL UNIQUE
);

-- 高校表
CREATE TABLE IF NOT EXISTS schools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    province_id INTEGER REFERENCES provinces(id),
    city VARCHAR(50),
    level VARCHAR(20),          -- 本科/专科
    type VARCHAR(20),           -- 综合/理工/师范/医药/农林/财经/政法/语言/艺术/体育/民族
    is_985 INTEGER DEFAULT 0,
    is_211 INTEGER DEFAULT 0,
    is_double_first_class INTEGER DEFAULT 0,
    website VARCHAR(200),
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_schools_province ON schools(province_id);
CREATE INDEX IF NOT EXISTS idx_schools_name ON schools(name);
CREATE INDEX IF NOT EXISTS idx_schools_985 ON schools(is_985);
CREATE INDEX IF NOT EXISTS idx_schools_211 ON schools(is_211);
CREATE INDEX IF NOT EXISTS idx_schools_df ON schools(is_double_first_class);

-- 专业目录表
CREATE TABLE IF NOT EXISTS majors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    discipline VARCHAR(20),      -- 学科门类
    degree_type VARCHAR(20),
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_majors_name ON majors(name);
CREATE INDEX IF NOT EXISTS idx_majors_discipline ON majors(discipline);

-- 录取分数线表
CREATE TABLE IF NOT EXISTS admission_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id INTEGER NOT NULL REFERENCES schools(id),
    province_id INTEGER NOT NULL REFERENCES provinces(id),
    year INTEGER NOT NULL,
    category VARCHAR(10) NOT NULL,   -- 理科/文科/综合
    batch VARCHAR(20),
    min_score REAL,
    avg_score REAL,
    max_score REAL,
    min_rank INTEGER,
    source VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(school_id, province_id, year, category, batch)
);
CREATE INDEX IF NOT EXISTS idx_as_school ON admission_scores(school_id);
CREATE INDEX IF NOT EXISTS idx_as_province_year ON admission_scores(province_id, year);

-- 批次线表
CREATE TABLE IF NOT EXISTS batch_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    province_id INTEGER NOT NULL REFERENCES provinces(id),
    year INTEGER NOT NULL,
    category VARCHAR(10) NOT NULL,
    batch VARCHAR(20) NOT NULL,
    score INTEGER NOT NULL,
    UNIQUE(province_id, year, category, batch)
);

-- 一分一段表
CREATE TABLE IF NOT EXISTS one_point_tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    province_id INTEGER NOT NULL REFERENCES provinces(id),
    year INTEGER NOT NULL,
    category VARCHAR(10) NOT NULL,
    score INTEGER NOT NULL,
    cumulative_rank INTEGER NOT NULL,
    section_count INTEGER,
    UNIQUE(province_id, year, category, score)
);
CREATE INDEX IF NOT EXISTS idx_opt_query ON one_point_tables(province_id, year, category, score);
