CREATE TABLE universities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);
\echo '--> TABLE: universities created.';

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    google_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    department VARCHAR(100),
    profile_image_url TEXT, -- 使用 TEXT 儲存圖片 URL 或 Base64
    is_admin BOOLEAN DEFAULT FALSE
);
\echo '--> TABLE: users created.';

CREATE TABLE professors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(100),
    university_id INTEGER REFERENCES universities(id) ON DELETE SET NULL
);
\echo '--> TABLE: professors created.';

CREATE TABLE labs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(100),
    is_recruiting BOOLEAN DEFAULT TRUE,
    university_id INTEGER REFERENCES universities(id) ON DELETE SET NULL,
    cover_image_url TEXT
);
\echo '--> TABLE: labs created.';

CREATE TABLE lab_images (
    id SERIAL PRIMARY KEY,
    lab_id INTEGER NOT NULL REFERENCES labs(id) ON DELETE CASCADE,
    uploader_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    image_url TEXT NOT NULL,
    description TEXT,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
\echo '--> TABLE: lab_images created.';

CREATE TABLE reviews (
    review_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    professor_id INTEGER REFERENCES professors(id) ON DELETE CASCADE,
    lab_id INTEGER REFERENCES labs(id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
\echo '--> TABLE: reviews created.';

CREATE TABLE review_backup (
    backup_id SERIAL PRIMARY KEY,
    review_id INTEGER,
    user_id INTEGER,
    content TEXT NOT NULL,
    rating INTEGER,
    professor_id INTEGER,
    lab_id INTEGER,
    timestamp TIMESTAMP,
    archived_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
\echo '--> TABLE: review_backup created.';


-- === STAGE 3: DATA SEEDING (資料預置) ===
\echo '==> Seeding universities data...';
INSERT INTO universities (name) VALUES
('國立臺灣大學'), ('國立成功大學'), ('國立清華大學'), ('國立陽明交通大學'),
('國立臺灣師範大學'), ('國立中興大學'), ('國立中央大學'), ('國立中山大學'),
('國立政治大學'), ('國立臺灣科技大學'), ('國立臺北科技大學'), ('國立臺灣海洋大學'),
('國立中正大學'), ('國立東華大學'), ('國立暨南國際大學'), ('國立嘉義大學'),
('國立高雄大學'), ('國立臺北大學'), ('國立宜蘭大學'), ('國立聯合大學'),
('國立臺南大學'), ('國立臺東大學'), ('國立屏東大學'), ('國立金門大學'),
('臺北市立大學'), ('高雄市立大學'), ('國立臺灣藝術大學'), ('國立臺北藝術大學'),
('國立臺南藝術大學'), ('國立體育大學'), ('國立臺灣體育運動大學'),
('國立臺北教育大學'), ('國立臺中教育大學'),
('國立臺北護理健康大學'), ('國立高雄餐旅大學'), ('國立高雄科技大學'),
('東海大學'), ('輔仁大學'), ('東吳大學'), ('中原大學'), ('淡江大學'),
('逢甲大學'), ('靜宜大學'), ('長庚大學'), ('元智大學'), ('大同大學'),
('中國文化大學'), ('義守大學'), ('世新大學'), ('銘傳大學'), ('實踐大學'),
('朝陽科技大學'), ('南臺科技大學'), ('崑山科技大學'), ('嘉南藥理大學'), ('樹德科技大學'),
('龍華科技大學'), ('輔英科技大學'), ('明新科技大學'), ('健行科技大學'), ('正修科技大學'),
('萬能科技大學'), ('建國科技大學'), ('大仁科技大學'), ('聖約翰科技大學'),
('嶺東科技大學'), ('中國科技大學'), ('中臺科技大學'), ('臺北城市科技大學'), ('遠東科技大學'),
('元培醫事科技大學'), ('景文科技大學'), ('中華醫事科技大學'), ('東南科技大學'), ('德明財經科技大學'),
('明志科技大學'), ('大葉大學'), ('中華大學'), ('華梵大學'), ('玄奘大學'),
('亞洲大學'), ('開南大學'), ('佛光大學'), ('南華大學'), ('真理大學'),
('慈濟大學'), ('臺北醫學大學'), ('中山醫學大學'), ('中國醫藥大學'), ('高雄醫學大學'),
('長榮大學'), ('大同技術學院'), ('臺灣警察專科學校'), ('國防大學');
\echo '--> Inserted university data.';


-- === STAGE 4: VIEWS (建立檢視) ===
CREATE OR REPLACE VIEW professor_ranking AS
SELECT p.id, p.name, u.name as university_name, p.department, ROUND(AVG(r.rating), 2) AS avg_rating, COUNT(r.review_id) AS review_count
FROM professors p
LEFT JOIN reviews r ON r.professor_id = p.id
LEFT JOIN universities u ON p.university_id = u.id
GROUP BY p.id, u.name
ORDER BY avg_rating DESC;
\echo '--> VIEW: professor_ranking created.';

CREATE OR REPLACE VIEW top_labs_by_review AS
SELECT l.id, l.name, u.name as university_name, l.department, COUNT(r.review_id) AS review_count
FROM labs l
LEFT JOIN reviews r ON r.lab_id = l.id
LEFT JOIN universities u ON l.university_id = u.id
GROUP BY l.id, u.name
ORDER BY review_count DESC;
\echo '--> VIEW: top_labs_by_review created.';

\echo '==> Schema setup completed successfully!';