import traceback
from flask import Flask, render_template, request, jsonify, session, send_from_directory, g, make_response
import sqlite3
import os
import re
import io
import uuid
import json
from functools import wraps
from flask import redirect, session, jsonify
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DB_PATH = os.path.join(BASE_DIR, 'shop.db')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder='.', static_url_path='')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.environ.get('app_key') or 'dev-secret-change-me'

app_key = ""

cloudinary.config( 
  cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'), 
  api_key = os.environ.get('CLOUDINARY_API_KEY'), 
  api_secret = os.environ.get('CLOUDINARY_API_SECRET') 
)

DRIVE_KEY_FILE = 'drive_key.json'   # service account json
DRIVE_FILE_ID = '1JOpQkUdPGSt7xR8W-mtjTSsMKMp99bOt'
CREDENTIALS_FILE_ID = '1W0zA9o0MUvE9porLC56PPZsMEu8FYPOu'
PRODUCTS_FILE_ID = '1SU73aRyb5BH3HIfMIagGYpv9Oy63nXuY'
IMAGES_FOLDER_ID = '1Pk3Xlqp4jjjTk9hIKH5yUrOWF3FgdcYC'
SCOPES = ['https://www.googleapis.com/auth/drive']



def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        DRIVE_KEY_FILE, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=creds)


creds = service_account.Credentials.from_service_account_file(
    DRIVE_KEY_FILE,
    scopes=SCOPES
)

drive_service = build('drive', 'v3', credentials=creds)

@app.route('/')
def home():
    # Ye aapke index.html ko default page banayega
    return send_from_directory('.', 'index.html')

# Agar aapke paas aur HTML files hain (jaise admin.html)
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

def read_json_from_drive(file_id):
    service = get_drive_service()
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)
        content = fh.read().decode()
        return json.loads(content) if content else []
    except Exception as e:
        print(f"Error reading Drive file: {e}")
        return []
    

def write_json_to_drive(file_id, data):
    service = get_drive_service()
    fh = io.BytesIO(json.dumps(data, indent=2).encode())
    media = MediaIoBaseUpload(fh, mimetype='application/json', resumable=False)
    service.files().update(fileId=file_id, media_body=media).execute()

@app.route('/api/track-affiliate', methods=['POST'])
def track_affiliate():
    data = request.get_json(force=True)
    ref = data.get('ref')

    if not ref:
        return jsonify({'ok': False})

    # ek baar set ho jaaye to overwrite mat karo
    if 'affiliate_ref' not in session:
        session['affiliate_ref'] = ref

    return jsonify({'ok': True})

def calculate_commission(price, quantity, rate=0.10):
    try:
        price = float(price)
        quantity = int(quantity)
        commission = price * quantity * rate
        return round(commission, 2)
    except Exception:
        return 0.0


@app.route('/api/order', methods=['POST'])
def place_order():
    affiliate_id = session.get('affiliate_ref')
    data = request.get_json(force=True)

    price = data.get("price")
    quantity = data.get("quantity", 1)
    commission = 0
    commission_rate = 0.10

    if affiliate_id:
        commission = calculate_commission(price, quantity, commission_rate)

    order = {
        "order_id": "ORD_" + __import__('uuid').uuid4().hex[:10],
        "product_id": data.get("product_id"),
        "affiliate_id": session.get('affiliate_ref'),
        "product_title": data.get("product_title"),
        "price": data.get("price"),
        "status": "pending",
        "commission_rate": commission_rate if affiliate_id else 0,
        "commission_amount": commission,
        "size": data.get("size"),
        "quantity": data.get("quantity"),
        "buyer": {
            "name": data.get("name"),
            "mobile": data.get("mobile"),
            "address": data.get("address")
        },
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }

    orders = read_json_from_drive(DRIVE_FILE_ID)

    if not isinstance(orders, list):
        orders = []

        # Ab direct order append karo
    orders.append(order)

    write_json_to_drive(DRIVE_FILE_ID, orders)

    return jsonify({"ok": True, "order_id": order["order_id"], "ok": True,
        "affiliate_tracked": bool(affiliate_id), "commission": commission})



@app.route('/api/admin/status')
def api_admin_status():
    # simple status check for session-authenticated admin
    if 'admin_id' in session:
        return jsonify({'ok': True})
    return jsonify({'ok': False}), 401



@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect('/admin.html')
    
    # Fresh response banayein
    response = make_response(render_template('admin_dashboard.html'))
    # Cache khatam karne ke liye headers
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            return redirect('/admin.html')
        return f(*args, **kwargs)
    return wrapper


@app.route('/affiliate_dashboard')
def affiliate_dashboard():
    if session.get('role') != 'affiliate':
        return redirect('/admin.html')
    return render_template('affiliate_dashboard.html')

@app.route('/api/admin/login', methods=['POST'])
def api_admin_login():
    data = request.get_json(force=True)
    user = data.get('user', '').strip()
    pin = data.get('pin', '').strip()

    creds_data = read_json_from_drive(CREDENTIALS_FILE_ID)

    # 🔐 Admin check
    for admin in creds_data.get('admin', []):
        if admin['user'] == user and admin['pin'] == pin:
            session['role'] = 'admin'
            session['admin_id'] = admin['id']
            return jsonify({
                'ok': True,
                'role': 'admin',
                'redirect': '/admin_dashboard'
            })

    # 🔐 Affiliate check
    for aff in creds_data.get('affiliate', []):
        if aff['user'] == user and aff['pin'] == pin:
            session['role'] = 'affiliate'
            session['affiliate_id'] = aff['id']
            return jsonify({
                'ok': True,
                'role': 'affiliate',
                'affiliate_id': aff['id'],
                'redirect': '/affiliate_dashboard'
            })

    return jsonify({'ok': False, 'msg': 'Invalid phone or PIN'}), 401


@app.route('/api/admin/logout')
def api_admin_logout():
    session.pop('admin_id', None)
    return jsonify({'ok':True})


def require_admin():
    return 'admin_id' in session

def upload_image_to_cloudinary(f):
    try:
        # Direct upload bina kisi quota tension ke
        result = cloudinary.uploader.upload(f)
        return result['secure_url'] # Ye direct image ka link return karega
    except Exception as e:
        print(f"Cloudinary Error: {e}")
        return None

@app.route('/api/admin/upload', methods=['POST'])
def api_admin_upload():
    if not require_admin():
        return jsonify({'ok':False,'msg':'Unauthorized'}), 401
    
    form = request.form
    title = form.get('title','').strip()
    if not title: return jsonify({'ok': False, 'error': 'title_required'}), 400

    # Handle Images: Drive par upload karein
    images_files = request.files.getlist('images') + request.files.getlist('images[]')
    saved_ids = []
    last_error = "Unknown error"

    for f in images_files:
        if f and f.filename:
            try:
                # Cloudinary par upload
                upload_result = cloudinary.uploader.upload(f, folder="products",
    quality="auto:eco",      # <--- Best quality with lowest size
    fetch_format="auto",     # <--- Sahi format (webp etc.)
    width=800,               # <--- Website ke liye 800px kaafi hai
    crop="limit")
                image_url = upload_result.get('secure_url')
                saved_ids.append(image_url)
            except Exception as e:
                # Ab 'e' sirf is block ke andar hai, koi error nahi aayega
                print(f"FULL ERROR: {traceback.format_exc()}")
                return jsonify({
                    'ok': False, 
                    'msg': 'Image upload failed', 
                    'error': str(e)
                }), 500

    # Product Object
    pid = 'p_' + uuid.uuid4().hex[:12]
    new_product = {
        'id': pid,
        'title': title,
        'sku': form.get('sku','').strip(),
        'category': form.get('category','').strip(),
        'description': form.get('description','').strip(),
        'price': float(form.get('price') or 0),
        'original_price': float(form.get('originalPrice') or 0),
        'size_required': form.get('sizeRequired') == 'yes',
        'sizes': [s.strip() for s in (form.get('sizes') or '').split(',') if s.strip()],
        'quantity': int(form.get('quantity') or 0),
        'tags': [t.strip() for t in (form.get('tags') or '').split(',') if t.strip()],
        'images': saved_ids, # Yahan Drive ki IDs hain
        'created_at': form.get('createdAt') or __import__('datetime').datetime.utcnow().isoformat()
    }

    # Drive par update karein
    all_products = read_json_from_drive(PRODUCTS_FILE_ID)

    if not isinstance(all_products, list):
        all_products = []

    all_products.append(new_product)
    write_json_to_drive(PRODUCTS_FILE_ID, all_products)
    
    return jsonify({'ok':True, 'id': pid})

@app.route('/api/products')
def api_products():
    products = read_json_from_drive(PRODUCTS_FILE_ID)
    if not products:
        return jsonify([])
    
    # Yahan koi extra string concat (+ /uploads/) nahi karni hai
    # Kyunki products[i]['images'] mein pehle se 'https://...' hai
    return jsonify(products[::-1])

@app.route('/api/admin/product/<pid>')
def api_get_product(pid):
    products = read_json_from_drive(PRODUCTS_FILE_ID)
    p = next((item for item in products if item["id"] == pid), None)
    if not p: return jsonify({'ok': False, 'msg': 'Not found'}), 404
    
    # Links for frontend
    display_p = p.copy()
    display_p['images'] = [f'https://lh3.googleusercontent.com/u/0/d/{img_id}' for img_id in p['images']]
    return jsonify({'ok': True, 'product': display_p})

@app.route('/api/admin/update', methods=['POST'])
def api_admin_update():
    if not require_admin(): return jsonify({'ok': False, 'msg': 'Unauthorized'}), 401
    
    form = request.form
    prod_id = form.get('id')
    
    products = read_json_from_drive(PRODUCTS_FILE_ID)
    idx = next((i for i, item in enumerate(products) if item["id"] == prod_id), None)
    if idx is None: return jsonify({'ok': False, 'msg': 'Not found'}), 404

    # Handle New Images
    images_files = request.files.getlist('images') + request.files.getlist('images[]')
    new_ids = []
    for f in images_files:
        if f and f.filename:
            new_ids.append(upload_image_to_cloudinary(f))

    # Update Data
    products[idx].update({
        'title': form.get('title','').strip(),
        'sku': form.get('sku','').strip(),
        'category': form.get('category','').strip(),
        'description': form.get('description','').strip(),
        'price': float(form.get('price') or 0),
        'original_price': float(form.get('originalPrice') or 0),
        'size_required': form.get('sizeRequired') == 'yes',
        'sizes': [s.strip() for s in (form.get('sizes') or '').split(',') if s.strip()],
        'quantity': int(form.get('quantity') or 0),
        'tags': [t.strip() for t in (form.get('tags') or '').split(',') if t.strip()],
        'images': list(set(products[idx]['images'] + new_ids)) # Merge IDs
    })

    write_json_to_drive(PRODUCTS_FILE_ID, products)
    return jsonify({'ok': True})

@app.route('/api/admin/product/<pid>', methods=['DELETE'])
def api_admin_delete(pid):
    if not require_admin(): return jsonify({'ok': False, 'msg': 'Unauthorized'}), 401
    
    products = read_json_from_drive(PRODUCTS_FILE_ID)
    filtered_products = [p for p in products if p['id'] != pid]
    
    # Optional: Yahan Drive se images bhi delete karne ka code daal sakte hain
    
    write_json_to_drive(PRODUCTS_FILE_ID, filtered_products)
    return jsonify({'ok': True})


@app.route('/affiliate_dashboard_data', methods=['POST'])
def affiliate_dashboard_data():
    # 1. Frontend se ID lena
    affiliate_id = request.json.get('affiliate_id') 

    # 2. Drive se data read karna
    data = read_json_from_drive(DRIVE_FILE_ID)

    # --- YAHAN CHANGE HAI ---
    # Agar data list hai toh use 'orders' man lo, warna khali list
    if isinstance(data, list):
        orders = data
    else:
        orders = []
    # ------------------------

    completed_orders = 0
    pending_orders = 0
    this_month_earning = 0
    estimated_earning = 0

    print("AFFILIATE_ID_FROM_FRONTEND:", affiliate_id)

    for order in orders:
        # Check karna ki order is affiliate ka hai ya nahi
        if order.get('affiliate_id') != affiliate_id:
            continue

        # Commission calculate karna
        commission = float(order.get('commission_amount', 0))
        estimated_earning += commission

        status = order.get('status', 'pending')

        if status == 'completed':
            completed_orders += 1
            this_month_earning += commission
        elif status == 'pending':
            pending_orders += 1

    return jsonify({
        'ok': True,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
        'this_month_earning': round(this_month_earning, 2),
        'estimated_earning': round(estimated_earning, 2)
    })

if __name__ == '__main__':

    app.run(debug=True, port=8080)











