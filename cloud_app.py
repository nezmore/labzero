# cloud_app.py
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify

app = Flask(__name__)

# Fetch the live connection string from Render environment configurations
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://bloodtransfusionservice_user:NHANFq1httMcsPGoNPMHWfO5tlavk6SV@dpg-d88ne43eo5us7384h7f0-a/bloodtransfusionservice')

def get_db_connection():
    # Render requires explicit SSL protection for internal/external traffic
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

@app.route('/api/v1/ping', methods=['GET'])
def ping():
    """Endpoint used by laptops/phones to verify if they have internet connection"""
    return jsonify({"status": "online", "message": "ZNBTS National Cloud Engine Active"}), 200

@app.route('/api/v1/sync/upload', methods=['POST'])
def sync_upload():
    """Handles batches of incoming offline data from field teams"""
    payload = request.get_json() or {}
    donors = payload.get('donors', [])
    screenings = payload.get('screenings', [])
    donations = payload.get('donations', [])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Sync Donors Batch (Using UPSERT logic to handle conflict overrides automatically)
        for d in donors:
            cursor.execute('''
                INSERT INTO donors (donor_id, national_id, first_name, last_name, date_of_birth, gender, blood_group, phone, email, address, city, province, emergency_contact_name, emergency_contact_phone)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (donor_id) DO UPDATE SET
                    phone = EXCLUDED.phone,
                    email = EXCLUDED.email,
                    address = EXCLUDED.address,
                    last_updated = CURRENT_TIMESTAMP;
            ''', (d['donor_id'], d['national_id'], d['first_name'], d['last_name'], d['date_of_birth'], d['gender'], d['blood_group'], d['phone'], d['email'], d['address'], d['city'], d['province'], d['emergency_contact_name'], d['emergency_contact_phone']))
        
        # 2. Sync Screenings
        for s in screenings:
            cursor.execute('''
                INSERT INTO eligibility_screening (screening_id, donor_id, screening_date, screened_by, eligible, deferral_type, deferral_reason, deferral_until, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (screening_id) DO NOTHING;
            ''', (s['screening_id'], s['donor_id'], s['screening_date'], s['screened_by'], s['eligible'], s['deferral_type'], s['deferral_reason'], s['deferral_until'], s['notes']))
            
        # 3. Sync Donations
        for dn in donations:
            cursor.execute('''
                INSERT INTO donations (donation_id, donor_id, donation_date, donation_site, donation_type, volume_ml, blood_group_confirmed, hemoglobin_level, blood_pressure, pulse_rate, body_temp, collected_by, unit_number, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (donation_id) DO NOTHING;
            ''', (dn['donation_id'], dn['donor_id'], dn['donation_date'], dn['donation_site'], dn['donation_type'], dn['volume_ml'], dn['blood_group_confirmed'], dn['hemoglobin_level'], dn['blood_pressure'], dn['pulse_rate'], dn['body_temp'], dn['collected_by'], dn['unit_number'], dn['notes']))
            
        conn.commit()
        return jsonify({"status": "success", "message": f"Successfully integrated data packages into national database."}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)