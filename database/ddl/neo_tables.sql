-- DDL Script -- A normalized database schema (3NF) for NASA NEO data

-- Table 1: Asteroids (Main entity)
-- Stores unique asteroid information
CREATE TABLE IF NOT EXISTS asteroids (
    neo_id TEXT PRIMARY KEY,
    neo_reference_id TEXT NOT NULL,
    name TEXT NOT NULL,
    nasa_jpl_url TEXT,
    absolute_magnitude_h REAL,
    is_potentially_hazardous BOOLEAN NOT NULL,
    is_sentry_object BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookups by name
CREATE INDEX IF NOT EXISTS idx_asteroid_name ON asteroids(name);
CREATE INDEX IF NOT EXISTS idx_potentially_hazardous ON asteroids(is_potentially_hazardous);

-- Table 2: Estimated Diameters
-- Separated to avoid repeating unit conversions (2NF)
CREATE TABLE IF NOT EXISTS estimated_diameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    neo_id TEXT NOT NULL,
    unit TEXT NOT NULL, -- 'kilometers', 'meters', 'miles', 'feet'
    estimated_diameter_min REAL NOT NULL,
    estimated_diameter_max REAL NOT NULL,
    FOREIGN KEY (neo_id) REFERENCES asteroids(neo_id) ON DELETE CASCADE,
    UNIQUE(neo_id, unit)
);

-- Index for faster lookups by neo_id
CREATE INDEX IF NOT EXISTS idx_diameter_neo_id ON estimated_diameters(neo_id);

-- Table 3: Close Approaches
-- One asteroid can have multiple close approaches (1-to-many relationship)
CREATE TABLE IF NOT EXISTS close_approaches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    neo_id TEXT NOT NULL,
    close_approach_date DATE NOT NULL,
    close_approach_date_full TEXT,
    epoch_date_close_approach BIGINT,
    
    -- Relative velocity
    velocity_km_per_sec REAL,
    velocity_km_per_hour REAL,
    velocity_miles_per_hour REAL,
    
    -- Miss distance
    miss_distance_astronomical REAL,
    miss_distance_lunar REAL,
    miss_distance_km REAL,
    miss_distance_miles REAL,
    
    orbiting_body TEXT NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (neo_id) REFERENCES asteroids(neo_id) ON DELETE CASCADE,
    UNIQUE(neo_id, close_approach_date, orbiting_body)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_close_approach_date ON close_approaches(close_approach_date);
CREATE INDEX IF NOT EXISTS idx_close_approach_neo_id ON close_approaches(neo_id);
CREATE INDEX IF NOT EXISTS idx_orbiting_body ON close_approaches(orbiting_body);

-- Table 4: API Metadata
-- Track API calls to implement incremental loading
CREATE TABLE IF NOT EXISTS api_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    api_endpoint TEXT NOT NULL,
    element_count INTEGER,
    extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK(status IN ('success', 'partial', 'failed')) DEFAULT 'success',
    error_message TEXT,
    UNIQUE(start_date, end_date, api_endpoint)
);

-- Index for checking already-loaded date ranges
CREATE INDEX IF NOT EXISTS idx_api_metadata_dates ON api_metadata(start_date, end_date);

-- Table 5: Raw Data Archive (Optional - for audit trail)
-- Stores the original JSON response for data lineage
CREATE TABLE IF NOT EXISTS raw_data_archive (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    raw_json TEXT NOT NULL,
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Views for easier querying

-- View 1: Complete asteroid information with all close approaches
CREATE VIEW IF NOT EXISTS v_asteroid_close_approaches AS
SELECT 
    a.neo_id,
    a.name,
    a.absolute_magnitude_h,
    a.is_potentially_hazardous,
    ca.close_approach_date,
    ca.miss_distance_km,
    ca.velocity_km_per_hour,
    ca.orbiting_body
FROM asteroids a
JOIN close_approaches ca ON a.neo_id = ca.neo_id;

-- View 2: Potentially hazardous asteroids with their closest approaches
CREATE VIEW IF NOT EXISTS v_hazardous_asteroids AS
SELECT 
    a.neo_id,
    a.name,
    a.absolute_magnitude_h,
    MIN(ca.miss_distance_km) as closest_miss_distance_km,
    ca.close_approach_date as closest_approach_date
FROM asteroids a
JOIN close_approaches ca ON a.neo_id = ca.neo_id
WHERE a.is_potentially_hazardous = 1
GROUP BY a.neo_id, a.name, a.absolute_magnitude_h, ca.close_approach_date;