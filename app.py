#!/usr/bin/env python3
"""
LabZero Desktop — Zambia National Blood Donor Management System
A product of OneZero Group

Standalone desktop application. Double-click to run.
No browser, no command line needed.
"""

import os
import sys
import sqlite3
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

# 1. HANDLE SYSTEM DIRECTORIES CORRECTLY
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    # Put the writable DB in the directory where the .exe actually sits
    EXE_DIR = os.path.dirname(sys.executable)
    DATABASE = os.path.join(EXE_DIR, 'blood_donor_system.db')
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE = os.path.join(BASE_DIR, 'blood_donor_system.db')

app = Flask(__name__, 
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static'))
app.secret_key = 'onezero-labzero-desktop-2026'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database if it doesn't exist"""
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        # Read the schema template embedded inside the bundle
        schema_path = os.path.join(BASE_DIR, 'schema.sql')
        if os.path.exists(schema_path):
            c.executescript(open(schema_path).read())
        conn.commit()
        conn.close()
        print("[LabZero] Database initialized successfully.")

def gen_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8].upper()}"

# ========================================================================
# ROUTES (Kept intact from your design core)
# ========================================================================

@app.route('/')
def dashboard():
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM donors')
    td = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM donations')
    tdn = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM deferrals WHERE lifted=0 AND (deferral_until IS NULL OR deferral_until>=date("now"))')
    ad = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT donation_site) FROM donations')
    ast = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM eligibility_screening WHERE eligible=0')
    dfc = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM eligibility_screening')
    ts = c.fetchone()[0]
    dr = round(dfc/ts*100,1) if ts>0 else 0
    c.execute('SELECT d.*,dn.first_name,dn.last_name,dn.blood_group FROM donations d JOIN donors dn ON d.donor_id=dn.donor_id ORDER BY d.donation_date DESC LIMIT 10')
    rd = [dict(r) for r in c.fetchall()]
    c.execute('SELECT donation_site,COUNT(*) as count FROM donations GROUP BY donation_site ORDER BY count DESC')
    ss = [dict(r) for r in c.fetchall()]
    c.execute('SELECT blood_group_confirmed,COUNT(*) as count FROM donations WHERE blood_group_confirmed IS NOT NULL GROUP BY blood_group_confirmed ORDER BY count DESC')
    bgs = [dict(r) for r in c.fetchall()]
    c.execute('SELECT strftime("%Y-%m",donation_date) as month,COUNT(*) as count FROM donations GROUP BY month ORDER BY month DESC LIMIT 12')
    mt = [dict(r) for r in c.fetchall()]
    mt.reverse()
    c.execute('SELECT df.*,dn.first_name,dn.last_name FROM deferrals df JOIN donors dn ON df.donor_id=dn.donor_id WHERE df.lifted=0 AND (df.deferral_until IS NULL OR df.deferral_until>=date("now")) ORDER BY df.deferral_date DESC LIMIT 10')
    rdf = [dict(r) for r in c.fetchall()]
    conn.close()
    return render_template('dashboard.html', total_donors=td, total_donations=tdn, active_deferrals=ad,
                          active_sites=ast, deferral_rate=dr, recent_donations=rd, site_stats=ss,
                          blood_group_stats=bgs, monthly_trend=mt, recent_deferrals=rdf)

@app.route('/donors')
def donors_list():
    conn = get_db(); c = conn.cursor()
    search = request.args.get('search','')
    bg = request.args.get('blood_group','')
    q = 'SELECT * FROM donors WHERE 1=1'; p = []
    if search:
        q += ' AND (first_name LIKE ? OR last_name LIKE ? OR national_id LIKE ? OR phone LIKE ?)'
        l = f'%{search}%'; p.extend([l,l,l,l])
    if bg: q += ' AND blood_group=?'; p.append(bg)
    q += ' ORDER BY created_at DESC'
    c.execute(q, p)
    donors = [dict(r) for r in c.fetchall()]
    c.execute('SELECT DISTINCT blood_group FROM donors WHERE blood_group IS NOT NULL ORDER BY blood_group')
    bgs = [r[0] for r in c.fetchall()]
    conn.close()
    return render_template('donors.html', donors=donors, blood_groups=bgs, search=search, blood_group=bg)

@app.route('/donors/register', methods=['GET','POST'])
def register_donor():
    if request.method == 'POST':
        conn = get_db(); c = conn.cursor()
        did = gen_id('DNR')
        c.execute('INSERT INTO donors (donor_id,national_id,first_name,last_name,date_of_birth,gender,blood_group,phone,email,address,city,province,emergency_contact_name,emergency_contact_phone) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                  (did, request.form.get('national_id'), request.form['first_name'], request.form['last_name'],
                   request.form['date_of_birth'], request.form['gender'], request.form.get('blood_group'),
                   request.form.get('phone'), request.form.get('email'), request.form.get('address'),
                   request.form.get('city'), request.form.get('province'), request.form.get('emergency_contact_name'),
                   request.form.get('emergency_contact_phone')))
        conn.commit(); conn.close()
        flash(f'Donor {request.form["first_name"]} {request.form["last_name"]} registered!', 'success')
        return redirect(url_for('donor_detail', donor_id=did))
    return render_template('register_donor.html')

@app.route('/donors/<donor_id>')
def donor_detail(donor_id):
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT * FROM donors WHERE donor_id=?', (donor_id,))
    r = c.fetchone(); donor = dict(r) if r else None
    if not donor: flash('Donor not found', 'error'); return redirect(url_for('donors_list'))
    c.execute('SELECT * FROM donations WHERE donor_id=? ORDER BY donation_date DESC', (donor_id,))
    donations = [dict(r) for r in c.fetchall()]
    c.execute('SELECT * FROM eligibility_screening WHERE donor_id=? ORDER BY screening_date DESC', (donor_id,))
    screenings = [dict(r) for r in c.fetchall()]
    c.execute('SELECT * FROM deferrals WHERE donor_id=? ORDER BY deferral_date DESC', (donor_id,))
    deferrals = [dict(r) for r in c.fetchall()]
    c.execute('SELECT * FROM consent_forms WHERE donor_id=? ORDER BY consent_date DESC', (donor_id,))
    consents = [dict(r) for r in c.fetchall()]
    last = donations[0] if donations else None
    ne = datetime.now().date()
    if last:
        ld = datetime.strptime(last['donation_date'], '%Y-%m-%d').date()
        ne = ld + timedelta(days=56)
    c.execute('SELECT * FROM deferrals WHERE donor_id=? AND lifted=0 AND (deferral_until IS NULL OR deferral_until>=date("now")) ORDER BY deferral_until DESC LIMIT 1', (donor_id,))
    ad = c.fetchone()
    is_def = False
    if ad:
        is_def = True
        if ad['deferral_until']:
            dd = datetime.strptime(ad['deferral_until'], '%Y-%m-%d').date()
            if dd > ne: ne = dd
    conn.close()
    return render_template('donor_detail.html', donor=donor, donations=donations, screenings=screenings,
                          deferrals=deferrals, consents=consents, total_donations=len(donations),
                          next_eligible=ne, is_deferred=is_def)

@app.route('/screening/<donor_id>', methods=['GET','POST'])
def screening(donor_id):
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT * FROM donors WHERE donor_id=?', (donor_id,))
    r = c.fetchone(); donor = dict(r) if r else None
    if not donor: flash('Donor not found', 'error'); return redirect(url_for('donors_list'))
    if request.method == 'POST':
        sid = gen_id('SCR')
        data = {
            'screened_by': request.form.get('screened_by'),
            'feeling_well_today': request.form.get('feeling_well_today')=='yes',
            'recent_illness': request.form.get('recent_illness')=='yes',
            'chronic_disease': request.form.get('chronic_disease')=='yes',
            'taking_medication': request.form.get('taking_medication')=='yes',
            'medication_details': request.form.get('medication_details'),
            'recent_surgery': request.form.get('recent_surgery')=='yes',
            'surgery_date': request.form.get('surgery_date'),
            'recent_travel': request.form.get('recent_travel')=='yes',
            'travel_details': request.form.get('travel_details'),
            'multiple_partners': request.form.get('multiple_partners')=='yes',
            'paid_for_sex': request.form.get('paid_for_sex')=='yes',
            'drug_use': request.form.get('drug_use')=='yes',
            'msm': request.form.get('msm')=='yes',
            'pregnant': request.form.get('pregnant')=='yes',
            'recent_childbirth': request.form.get('recent_childbirth')=='yes',
            'breastfeeding': request.form.get('breastfeeding')=='yes',
            'last_menstrual_period': request.form.get('last_menstrual_period'),
            'previous_reaction': request.form.get('previous_reaction')=='yes',
            'previous_reaction_details': request.form.get('previous_reaction_details'),
            'previous_deferral': request.form.get('previous_deferral')=='yes',
            'previous_deferral_reason': request.form.get('previous_deferral_reason'),
            'weight_kg': float(request.form.get('weight_kg',0)),
            'age_valid': request.form.get('age_valid')=='yes',
            'hemoglobin_ok': request.form.get('hemoglobin_ok')=='yes',
            'blood_pressure_ok': request.form.get('blood_pressure_ok')=='yes',
            'temperature_ok': request.form.get('temperature_ok')=='yes',
            'notes': request.form.get('notes')
        }
        eligible = calc_elig(data)
        dt = dr = du = dd = None
        if not eligible:
            di = det_def(data); dt = di['type']; dr = di['reason']; dd = di.get('duration_days')
            if dd: du = (datetime.now().date()+timedelta(days=dd)).isoformat()
        c.execute('INSERT INTO eligibility_screening (screening_id,donor_id,screened_by,feeling_well_today,recent_illness,chronic_disease,taking_medication,medication_details,recent_surgery,surgery_date,recent_travel,travel_details,multiple_partners,paid_for_sex,drug_use,msm,pregnant,recent_childbirth,breastfeeding,last_menstrual_period,previous_reaction,previous_reaction_details,previous_deferral,previous_deferral_reason,weight_kg,age_valid,hemoglobin_ok,blood_pressure_ok,temperature_ok,eligible,deferral_type,deferral_reason,deferral_until,deferral_duration_days,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                  (sid,donor_id,data['screened_by'],data['feeling_well_today'],data['recent_illness'],data['chronic_disease'],data['taking_medication'],data['medication_details'],data['recent_surgery'],data['surgery_date'],data['recent_travel'],data['travel_details'],data['multiple_partners'],data['paid_for_sex'],data['drug_use'],data['msm'],data['pregnant'],data['recent_childbirth'],data['breastfeeding'],data['last_menstrual_period'],data['previous_reaction'],data['previous_reaction_details'],data['previous_deferral'],data['previous_deferral_reason'],data['weight_kg'],data['age_valid'],data['hemoglobin_ok'],data['blood_pressure_ok'],data['temperature_ok'],eligible,dt,dr,du,dd,data['notes']))
        if not eligible:
            dfid = gen_id('DFR')
            c.execute('INSERT INTO deferrals (deferral_id,donor_id,screening_id,deferral_date,deferral_type,deferral_reason,deferral_until,deferral_duration_days) VALUES (?,?,?,?,?,?,?,?)',
                      (dfid,donor_id,sid,datetime.now().date().isoformat(),dt,dr,du,dd))
        conn.commit(); conn.close()
        if eligible: flash('Donor is ELIGIBLE to donate!', 'success')
        else: flash(f'Donor DEFERRED: {dr} ({dt})', 'warning')
        return redirect(url_for('donor_detail', donor_id=donor_id))
    conn.close()
    return render_template('screening.html', donor=donor)

def calc_elig(data):
    if data.get('drug_use'): return False
    if data.get('paid_for_sex'): return False
    if data.get('feeling_well_today')==False: return False
    if data.get('recent_illness'): return False
    if data.get('age_valid')==False: return False
    if data.get('hemoglobin_ok')==False: return False
    if data.get('weight_kg',0)<50: return False
    if data.get('pregnant'): return False
    if data.get('recent_childbirth'): return False
    if data.get('breastfeeding'): return False
    if data.get('recent_surgery') and data.get('surgery_date'):
        ds = (datetime.now().date()-datetime.strptime(data['surgery_date'],'%Y-%m-%d').date()).days
        if ds<180: return False
    return True

def det_def(data):
    if data.get('drug_use'): return {'type':'permanent','reason':'History of intravenous drug use'}
    if data.get('paid_for_sex'): return {'type':'permanent','reason':'History of paying for sexual services'}
    if data.get('pregnant'): return {'type':'temporary','reason':'Currently pregnant','duration_days':365}
    if data.get('recent_childbirth'): return {'type':'temporary','reason':'Recent childbirth','duration_days':180}
    if data.get('breastfeeding'): return {'type':'temporary','reason':'Currently breastfeeding','duration_days':180}
    if data.get('recent_illness'): return {'type':'temporary','reason':'Recent illness','duration_days':14}
    if data.get('hemoglobin_ok')==False: return {'type':'temporary','reason':'Low hemoglobin level','duration_days':120}
    if data.get('recent_surgery'): return {'type':'temporary','reason':'Recent surgery','duration_days':180}
    if data.get('weight_kg',0)<50: return {'type':'temporary','reason':'Below minimum weight requirement','duration_days':365}
    return {'type':'temporary','reason':'General deferral','duration_days':90}

@app.route('/donations')
def donations_list():
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT d.*,dn.first_name,dn.last_name,dn.blood_group FROM donations d JOIN donors dn ON d.donor_id=dn.donor_id ORDER BY d.donation_date DESC LIMIT 50')
    donations = [dict(r) for r in c.fetchall()]
    conn.close()
    return render_template('donations.html', donations=donations)

@app.route('/donations/record/<donor_id>', methods=['GET','POST'])
def record_donation(donor_id):
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT * FROM donors WHERE donor_id=?', (donor_id,))
    r = c.fetchone(); donor = dict(r) if r else None
    if not donor: flash('Donor not found', 'error'); return redirect(url_for('donors_list'))
    c.execute('SELECT * FROM deferrals WHERE donor_id=? AND lifted=0 AND (deferral_until IS NULL OR deferral_until>=date("now"))', (donor_id,))
    ad = c.fetchone()
    if ad:
        conn.close()
        flash(f'Donor is currently deferred: {ad["deferral_reason"]}', 'error')
        return redirect(url_for('donor_detail', donor_id=donor_id))
    c.execute('SELECT * FROM donations WHERE donor_id=? ORDER BY donation_date DESC LIMIT 1', (donor_id,))
    last = c.fetchone()
    if request.method == 'POST':
        if last:
            ld = datetime.strptime(last['donation_date'],'%Y-%m-%d').date()
            ds = (datetime.now().date()-ld).days
            if ds<56:
                conn.close()
                flash(f'Must wait {56-ds} more days before next donation', 'error')
                return redirect(url_for('donor_detail', donor_id=donor_id))
        did = gen_id('DON')
        c.execute('INSERT INTO donations (donation_id,donor_id,donation_date,donation_site,donation_type,volume_ml,blood_group_confirmed,hemoglobin_level,blood_pressure,pulse_rate,body_temp,collected_by,unit_number,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                  (did,donor_id,request.form.get('donation_date',datetime.now().date().isoformat()),request.form['donation_site'],request.form.get('donation_type','whole_blood'),request.form.get('volume_ml',450),request.form.get('blood_group_confirmed'),request.form.get('hemoglobin_level'),request.form.get('blood_pressure'),request.form.get('pulse_rate'),request.form.get('body_temp'),request.form.get('collected_by'),request.form.get('unit_number'),request.form.get('notes')))
        conn.commit(); conn.close()
        flash('Donation recorded successfully!', 'success')
        return redirect(url_for('donor_detail', donor_id=donor_id))
    c.execute('SELECT * FROM sites WHERE is_active=1 ORDER BY site_name')
    sites = [dict(r) for r in c.fetchall()]
    conn.close()
    ne = None
    if last:
        ld = datetime.strptime(last['donation_date'],'%Y-%m-%d').date()
        ne = ld + timedelta(days=56)
    return render_template('record_donation.html', donor=donor, sites=sites, last_donation=last, next_eligible=ne)

@app.route('/sites')
def sites_list():
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT * FROM sites ORDER BY created_at DESC')
    sites = [dict(r) for r in c.fetchall()]
    conn.close()
    return render_template('sites.html', sites=sites)

@app.route('/sites/add', methods=['POST'])
def add_site():
    conn = get_db(); c = conn.cursor()
    sid = gen_id('STE')
    c.execute('INSERT INTO sites (site_id,site_name,site_type,address,city,province,contact_person,contact_phone) VALUES (?,?,?,?,?,?,?,?)',
              (sid,request.form['site_name'],request.form['site_type'],request.form.get('address'),request.form['city'],request.form['province'],request.form.get('contact_person'),request.form.get('contact_phone')))
    conn.commit(); conn.close()
    flash('Site added successfully!', 'success')
    return redirect(url_for('sites_list'))

@app.route('/reports')
def reports():
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM donors')
    td = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM donations')
    tdn = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT donor_id) FROM donations')
    ud = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM eligibility_screening WHERE eligible=0')
    dfc = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM eligibility_screening')
    ts = c.fetchone()[0]
    dr = round(dfc/ts*100,1) if ts>0 else 0
    c.execute('SELECT donation_site,COUNT(*) as count,COUNT(DISTINCT donor_id) as unique_donors FROM donations GROUP BY donation_site ORDER BY count DESC')
    ss = [dict(r) for r in c.fetchall()]
    c.execute('SELECT blood_group_confirmed,COUNT(*) as count FROM donations WHERE blood_group_confirmed IS NOT NULL GROUP BY blood_group_confirmed ORDER BY count DESC')
    bs = [dict(r) for r in c.fetchall()]
    c.execute('SELECT strftime("%Y-%m",donation_date) as month,COUNT(*) as count,COUNT(DISTINCT donor_id) as unique_donors FROM donations GROUP BY month ORDER BY month DESC LIMIT 12')
    mo = [dict(r) for r in c.fetchall()]
    mo.reverse()
    c.execute('SELECT deferral_reason,COUNT(*) as count,deferral_type FROM deferrals GROUP BY deferral_reason ORDER BY count DESC')
    drs = [dict(r) for r in c.fetchall()]
    conn.close()
    return render_template('reports.html', total_donors=td, total_donations=tdn, unique_donors=ud,
                          deferral_rate=dr, deferred_count=dfc, site_stats=ss, blood_stats=bs, monthly=mo, deferral_reasons=drs)

@app.route('/api/donors/search')
def api_search():
    q = request.args.get('q','')
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT donor_id,first_name,last_name,national_id,blood_group,phone FROM donors WHERE first_name LIKE ? OR last_name LIKE ? OR national_id LIKE ? LIMIT 10',
              (f'%{q}%',f'%{q}%',f'%{q}%'))
    results = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(results)

@app.route('/api/stats')
def api_stats():
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM donors')
    d = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM donations')
    dn = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM deferrals WHERE lifted=0 AND (deferral_until IS NULL OR deferral_until>=date("now"))')
    df = c.fetchone()[0]
    conn.close()
    return jsonify({'donors':d,'donations':dn,'deferrals':df})

# ========================================================================
# DESKTOP LAUNCHER
# ========================================================================

def launch_desktop():
    """Launch the desktop window using webview"""
    import webview
    init_db()

    # Start Flask on a guaranteed local port
    from threading import Thread
    def run_server():
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

    server = Thread(target=run_server, daemon=True)
    server.start()

    # Give server a moment to boot
    import time
    time.sleep(1.5)

    # Launch desktop window matching the exact local port
    webview.create_window(
        'LabZero — Zambia National Blood Donor Management System',
        'http://127.0.0.1:5000/',
        width=1400,
        height=900,
        min_size=(1000, 600),
        text_select=True
    )
    webview.start()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        init_db()
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        try:
            launch_desktop()
        except ImportError:
            init_db()
            app.run(debug=True, host='0.0.0.0', port=5000)