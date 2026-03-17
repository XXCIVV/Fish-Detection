-- ตารางเก็บ Session การใช้งาน (เช่น การเปิดกล้อง 1 ครั้ง)
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    device_info TEXT
);

-- ตารางเก็บข้อมูลการตรวจจับในแต่ละ Session
CREATE TABLE IF NOT EXISTS detections (
    id SERIAL PRIMARY KEY,
    session_id TEXT,

    species_name TEXT NOT NULL,
    confidence REAL NOT NULL,

    bbox JSONB NOT NULL,

    image_path TEXT DEFAULT NULL,

    create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_session
        FOREIGN KEY (session_id)
        REFERENCES sessions(id)
        ON DELETE CASCADE
);

-- Index สำหรับ Dashboard Real-time
CREATE INDEX IF NOT EXISTS idx_session_id ON detections(session_id);
CREATE INDEX IF NOT EXISTS idx_species ON detections(species_name);

-- Index เพิ่มเติมสำหรับ JSONB
CREATE INDEX IF NOT EXISTS idx_bbox ON detections USING GIN(bbox);