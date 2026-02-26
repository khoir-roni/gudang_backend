from flask import Blueprint, request, jsonify, redirect, url_for, send_from_directory
from .models import Tool, History, User
import bcrypt
import os
import mimetypes

# Memastikan file JS dikirim dengan content-type yang benar (Fix untuk Windows)
mimetypes.add_type('application/javascript', '.js')

main = Blueprint('main', __name__)

# Middleware untuk mengatur routing berdasarkan Domain (Cloudflare)
@main.before_request
def route_traffic_by_domain():
    # Biarkan request OPTIONS (CORS Preflight) lewat
    if request.method == 'OPTIONS':
        return

    # Ambil Host dari Header (Prioritas X-Forwarded-Host dari Cloudflare)
    host = request.headers.get('X-Forwarded-Host', request.headers.get('Host', '')).lower()
    path = request.path
    
    # Konfigurasi Domain
    WEB_DOMAIN = 'gudangapp-hki.my.id'
    
    # Daftar Endpoint API
    api_endpoints = ['/get_barang', '/add_barang', '/update_barang', '/edit_barang', 
                     '/delete_barang', '/get_history', '/delete_history', '/login', '/register']

    # Skenario: User membuka link API (misal /get_barang) di Domain WEB -> Redirect ke Landing Page
    if WEB_DOMAIN in host and 'api.' not in host:
        if path in api_endpoints and request.method == 'GET':
            return redirect('/')

@main.route('/add_barang', methods=['POST'])
def add_barang():
    data = request.get_json()
    try:
        # Validasi field yang diperlukan
        required_fields = ['nama_barang', 'jumlah', 'lemari', 'lokasi', 'username']
        for field in required_fields:
            if field not in data:
                return jsonify({"message": f"Field '{field}' diperlukan"}), 400
        
        Tool.create(
            nama_barang=data['nama_barang'],
            jumlah=data['jumlah'],
            lemari=data['lemari'],
            lokasi=data['lokasi'],
            username=data['username']
        )
        return jsonify({"message": "Barang berhasil ditambahkan!"})
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@main.route('/get_barang', methods=['GET'])
def get_barang():
    try:
        tools = Tool.get_all()
        return jsonify(tools)
    except Exception as e:
        return jsonify({"message": "Error fetching barang"}), 500

@main.route('/update_barang', methods=['POST'])
def update_barang():
    data = request.get_json()
    print('==== update_barang DEBUG ====')
    print(f'Request data: {data}')
    
    try:
        # Validasi field yang diperlukan
        required_fields = ['nama_barang', 'jumlah', 'lemari', 'lokasi', 'username']
        for field in required_fields:
            if field not in data:
                return jsonify({"message": f"Field '{field}' diperlukan"}), 400
        
        result = Tool.update_stock(
            nama_barang=data['nama_barang'],
            jumlah=data['jumlah'],
            lemari=data['lemari'],
            lokasi=data['lokasi'],
            username=data['username']
        )
        print(f'Result: {result}')
        
        if isinstance(result, tuple):  # Jika ada error message dan status
            return jsonify(result[0]), result[1]
        return jsonify(result)
    except Exception as e:
        print(f'Error in update_barang: {str(e)}')
        return jsonify({"message": f"Error: {str(e)}"}), 500

@main.route('/edit_barang', methods=['POST'])
def edit_barang():
    data = request.get_json()
    try:
        result = Tool.edit(
            id=data.get('id'),
            nama_barang=data['nama_barang'],
            jumlah_baru=data['jumlah'],
            lemari=data['lemari'],
            lokasi=data['lokasi'],
            username=data['username']
        )
        if isinstance(result, tuple): return jsonify(result[0]), result[1]
        return jsonify(result)
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@main.route('/delete_barang', methods=['DELETE'])
def delete_barang():
    data = request.get_json()
    try:
        # Validasi field yang diperlukan
        required_fields = ['nama_barang', 'lemari', 'lokasi']
        for field in required_fields:
            if field not in data:
                return jsonify({"message": f"Field '{field}' diperlukan"}), 400
        
        Tool.delete(
            nama_barang=data['nama_barang'],
            lemari=data['lemari'],
            lokasi=data['lokasi']
        )
        return jsonify({"message": "Barang berhasil dihapus!"})
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@main.route('/get_history', methods=['GET'])
def get_history():
    try:
        history = History.get_all()
        return jsonify(history)
    except Exception as e:
        return jsonify({"message": "Error fetching history"}), 500

@main.route('/delete_history', methods=['DELETE'])
def delete_history():
    data = request.get_json()
    try:
        History.delete(data.get('id'))
        return jsonify({"message": "History berhasil dihapus!"})
    except Exception as e:
        return jsonify({"message": "Error deleting history"}), 500

@main.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    try:
        User.create(**data)
        return jsonify({"message": "User berhasil ditambahkan"}), 201
    except Exception as e:
        return jsonify({"message": f"Error: {e}"}), 500
    
@main.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.find_by_username(username)

    if user and bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):
        return jsonify({"message": "Login berhasil!", "token": str(user[0])})
    else:
        return jsonify({"message": "Username atau password salah"}), 401

# @main.route('/')
# def index():
#     return jsonify({
#         "status": "online",
#         "message": "Server Gudang Berjalan!",
#         "version": "1.0"
#     })


# Tentukan lokasi folder build secara dinamis
# os.path.dirname(__file__) mendapatkan lokasi folder 'backend'
# '..' digunakan untuk naik satu tingkat ke folder utama 'gudang_app'
# NOTE: Adjusted path to go up two levels from 'app' to 'gudangwarehouse' root, then into 'frontend_web'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cek apakah folder build tersedia (Production), jika tidak gunakan folder source 'web'
BUILD_DIR = os.path.join(BASE_DIR, '..', '..', 'gudang_frontend_web', 'build', 'web')
SOURCE_DIR = os.path.join(BASE_DIR, '..', '..', 'gudang_frontend_web', 'web')

# Catch-all route untuk melayani file statis Flutter ATAU fallback ke index.html (SPA)
# Penting: Route ini harus diletakkan paling bawah agar tidak menimpa route API
@main.route('/<path:path>')
def serve_static(path):
    host = request.headers.get('X-Forwarded-Host', request.headers.get('Host', '')).lower()
    
    # Skenario: Akses path sembarang di API Domain -> Return 404 JSON (Bukan HTML)
    if 'api.gudangapp-hki.my.id' in host:
        return jsonify({"message": "Endpoint not found"}), 404

    # Cek folder build setiap request agar tidak perlu restart server setelah build
    static_dir = BUILD_DIR if os.path.exists(BUILD_DIR) else SOURCE_DIR
    
    # 1. Cek apakah path merujuk ke file fisik yang ada (assets, js, css)
    file_path = os.path.join(static_dir, path)
    
    if os.path.exists(file_path) and not os.path.isdir(file_path):
        return send_from_directory(static_dir, path)
    
    # Jika file dengan ekstensi tidak ditemukan (misal .js, .css), return 404
    # Jangan return index.html, karena browser akan error "Unexpected token <"
    if '.' in path:
        return "File not found", 404

    # 2. Jika file tidak ditemukan, kembalikan index.html (untuk routing Flutter/SPA)
    # Ini menangani kasus refresh page pada route seperti /login atau /inventory
    return send_from_directory(static_dir, 'index.html')

# Route khusus untuk root URL '/'
@main.route('/')
def serve_root():
    host = request.headers.get('X-Forwarded-Host', request.headers.get('Host', '')).lower()

    # Skenario: Akses Root di API Domain -> Return JSON Status
    if 'api.gudangapp-hki.my.id' in host:
        return jsonify({
            "status": "online",
            "message": "Gudang API Service is Running",
            "version": "1.0"
        })

    static_dir = BUILD_DIR if os.path.exists(BUILD_DIR) else SOURCE_DIR
    print(f"Serving Flutter from: {static_dir}") # Debug log untuk memastikan path benar
    return send_from_directory(static_dir, 'index.html')

# ... sisa endpoint API Anda (login, get_barang, dll) ...