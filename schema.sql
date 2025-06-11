-- === PART 1: Table Definitions with Constraints ===

-- 使用者表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    google_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    department VARCHAR(100),
    is_admin BOOLEAN DEFAULT FALSE
);

-- 教授表 (主鍵統一為 id)
CREATE TABLE professors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(100)
);

-- 【已修正】實驗室表名改為 labs，主鍵改為 id，與 Python 模型一致
CREATE TABLE labs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(100),
    is_recruiting BOOLEAN DEFAULT TRUE
);

-- 評價表 (更新外鍵參照)
CREATE TABLE reviews (
    review_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    content TEXT NOT NULL,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    professor_id INTEGER REFERENCES professors(id), -- 更新參照
    lab_id INTEGER REFERENCES labs(id),             -- 更新參照
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 評價備份表
CREATE TABLE review_backup (
    review_id SERIAL PRIMARY KEY,
    user_id INTEGER,
    content TEXT NOT NULL,
    rating INTEGER,
    professor_id INTEGER,
    lab_id INTEGER,
    timestamp TIMESTAMP
);

-- 觸發器：自動備份 30 天前的 review
CREATE OR REPLACE FUNCTION backup_old_reviews()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO review_backup (review_id, user_id, content, rating, professor_id, lab_id, timestamp)
    SELECT review_id, user_id, content, rating, professor_id, lab_id, timestamp
    FROM reviews
    WHERE timestamp < NOW() - INTERVAL '30 days';

    DELETE FROM reviews WHERE timestamp < NOW() - INTERVAL '30 days';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 在生產環境中，觸發器建議由排程任務取代，此處暫時註解
-- CREATE TRIGGER trg_backup_old_reviews
-- AFTER INSERT ON reviews
-- EXECUTE FUNCTION backup_old_reviews();


-- === PART 2: Views ===

-- 1. 評價統計排行（平均評分由高到低）
CREATE OR REPLACE VIEW professor_ranking AS
SELECT p.id, p.name, p.department, ROUND(AVG(r.rating), 2) AS avg_rating, COUNT(r.review_id) AS review_count
FROM professors p
LEFT JOIN reviews r ON r.professor_id = p.id
GROUP BY p.id
ORDER BY avg_rating DESC;


-- 2. 最近 30 天即將過期的評價（供觸發備份用）
CREATE OR REPLACE VIEW reviews_to_backup AS
SELECT * FROM reviews
WHERE timestamp < NOW() - INTERVAL '30 days';


-- 3. 評價次數最多的實驗室（JOIN 和統計）
CREATE OR REPLACE VIEW top_labs_by_review AS
SELECT l.id, l.name, l.department, COUNT(r.review_id) AS review_count
FROM labs l
LEFT JOIN reviews r ON r.lab_id = l.id
GROUP BY l.id
ORDER BY review_count DESC;
