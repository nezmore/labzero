-- schema_postgres.sql
CREATE TABLE IF NOT EXISTS donors (
    donor_id VARCHAR(50) PRIMARY KEY,
    national_id VARCHAR(50) UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(20),
    blood_group VARCHAR(10),
    phone VARCHAR(50),
    email VARCHAR(100),
    address TEXT,
    city VARCHAR(50),
    province VARCHAR(50),
    emergency_contact_name VARCHAR(100),
    emergency_contact_phone VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS eligibility_screening (
    screening_id VARCHAR(50) PRIMARY KEY,
    donor_id VARCHAR(50) REFERENCES donors(donor_id),
    screening_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    screened_by VARCHAR(100),
    eligible BOOLEAN DEFAULT TRUE,
    deferral_type VARCHAR(50),
    deferral_reason TEXT,
    deferral_until DATE,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS donations (
    donation_id VARCHAR(50) PRIMARY KEY,
    donor_id VARCHAR(50) REFERENCES donors(donor_id),
    donation_date DATE NOT NULL,
    donation_site VARCHAR(100) NOT NULL,
    donation_type VARCHAR(50) DEFAULT 'whole_blood',
    volume_ml INTEGER DEFAULT 450,
    blood_group_confirmed VARCHAR(10),
    hemoglobin_level VARCHAR(20),
    blood_pressure VARCHAR(20),
    pulse_rate VARCHAR(20),
    body_temp VARCHAR(20),
    collected_by VARCHAR(100),
    unit_number VARCHAR(50),
    notes TEXT
);