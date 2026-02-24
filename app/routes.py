from flask import Blueprint, request, jsonify
from .models import Tool, History, User
import bcrypt
import os
from flask import Flask, send_from_directory

main = Blueprint('main', __name__)

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
FLUTTER_WEB_DIR = os.path.join(BASE_DIR, '..', '..', 'gudang_frontend_web', 'build', 'web')

# Catch-all route untuk melayani file statis Flutter ATAU fallback ke index.html (SPA)
# Penting: Route ini harus diletakkan paling bawah agar tidak menimpa route API
@main.route('/<path:path>')
def serve_static(path):
    # 1. Cek apakah path merujuk ke file fisik yang ada (assets, js, css)
    file_path = os.path.join(FLUTTER_WEB_DIR, path)
    
    if os.path.exists(file_path) and not os.path.isdir(file_path):
        return send_from_directory(FLUTTER_WEB_DIR, path)
    
    # 2. Jika file tidak ditemukan, kembalikan index.html (untuk routing Flutter/SPA)
    # Ini menangani kasus refresh page pada route seperti /login atau /inventory
    return send_from_directory(FLUTTER_WEB_DIR, 'index.html')

# Route khusus untuk root URL '/'
@main.route('/')
def serve_root():
    return send_from_directory(FLUTTER_WEB_DIR, 'index.html')

# ... sisa endpoint API Anda (login, get_barang, dll) ...