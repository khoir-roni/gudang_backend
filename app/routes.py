from flask import Blueprint, request, jsonify, redirect, url_for, send_from_directory
from .models import Tool, History, User, MLHarvestLog, MLModelRelease
import bcrypt
import os
import json
import uuid
import datetime
from pathlib import Path
from werkzeug.utils import secure_filename
import mimetypes
import re

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
            username=data['username'],
            tipe=data.get('tipe', 'tool'),
            tgl_kalibrasi=data.get('tgl_kalibrasi')
        )
        return jsonify({"message": "Barang berhasil ditambahkan!"})
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@main.route('/get_barang', methods=['GET'])
def get_barang():
    try:
        tipe = request.args.get('tipe')
        tools = Tool.get_all(tipe=tipe)
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
            username=data['username'],
            tipe=data.get('tipe', 'tool'),
            tgl_kalibrasi=data.get('tgl_kalibrasi')
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

def get_ml_base_dir():
    # 1. Cek server path
    server_dir = Path(r"D:\gudangWarehouse\gudang_model_of_Tools_maintenance")
    if server_dir.exists():
        return server_dir
    # 2. Cek dev path
    dev_dir = Path(r"C:\dev\Saguling\INOVASI\stats\gudangwarehouse\gudang_model_of_Tools_maintenance")
    if dev_dir.exists():
        return dev_dir
    # 3. Fallback sibling
    sibling = Path(__file__).resolve().parent.parent.parent / "gudang_model_of_Tools_maintenance"
    return sibling

# --- ML OTA & ACTIVE LEARNING ENDPOINTS ---

@main.route('/api/ml/model/version', methods=['GET'])
def get_ml_model_version():
    """Mengembalikan informasi versi model ML aktif untuk update OTA."""
    try:
        active_model = MLModelRelease.get_active()
        if not active_model:
            ml_dir = get_ml_base_dir()
            version_file = ml_dir / "exported_model" / "version.json"
            if version_file.exists():
                with open(version_file, 'r', encoding='utf-8') as f:
                    active_model = json.load(f)
            else:
                return jsonify({"message": "Model belum tersedia"}), 404

        # Harmonize key names across versions (dual compatibility)
        model_name = active_model.get('model_filename') or active_model.get('model_file', 'mobilenet_float.tflite')
        labels_name = active_model.get('labels_filename') or active_model.get('labels_file', 'labels.txt')
        model_sha = active_model.get('model_sha256') or active_model.get('sha256', '')

        base_host = request.host_url.rstrip('/')
        active_model['model_filename'] = model_name
        active_model['labels_filename'] = labels_name
        active_model['model_sha256'] = model_sha
        active_model['model_download_url'] = f"{base_host}/api/ml/model/download/{model_name}"
        active_model['labels_download_url'] = f"{base_host}/api/ml/model/download/{labels_name}"
        return jsonify(active_model), 200
    except Exception as e:
        return jsonify({"message": f"Gagal mengambil versi model: {str(e)}"}), 500

@main.route('/api/ml/model/download/<filename>', methods=['GET'])
def download_ml_model(filename):
    """Melayani pengunduhan berkas model (.tflite) atau labels (.txt)."""
    try:
        clean_name = secure_filename(filename)
        ml_dir = get_ml_base_dir()
        model_dir = ml_dir / "exported_model"
        target_path = model_dir / clean_name

        if not target_path.exists():
            return jsonify({"message": f"Berkas {clean_name} tidak ditemukan"}), 404

        return send_from_directory(str(model_dir), clean_name, as_attachment=True)
    except Exception as e:
        return jsonify({"message": f"Gagal mengunduh berkas: {str(e)}"}), 500

@main.route('/api/ml/collect', methods=['POST'])
def collect_training_image():
    """
    Menerima foto dari kamera HP teknisi bersama label konfirmasi (ground truth).
    Menyimpan foto ke harvested_dataset/<label>/ dan mencatat log ke database.
    """
    try:
        if 'image' not in request.files:
            return jsonify({"message": "File 'image' diperlukan"}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({"message": "Nama file kosong"}), 400

        ground_truth_label = request.form.get('ground_truth_label')
        if not ground_truth_label:
            return jsonify({"message": "Field 'ground_truth_label' diperlukan"}), 400

        predicted_label = request.form.get('predicted_label')
        predicted_confidence = request.form.get('predicted_confidence')
        if predicted_confidence is not None:
            try:
                predicted_confidence = float(predicted_confidence)
            except ValueError:
                predicted_confidence = None

        uploaded_by = request.form.get('uploaded_by', 'anonymous')

        # Normalisasi label: ganti underscore dengan spasi, bersihkan karakter path tidak aman
        clean_label = ground_truth_label.strip().replace('_', ' ')
        clean_label = re.sub(r'[\\/*?:"<>|]', '', clean_label).strip()
        if not clean_label:
            clean_label = "Uncategorized"

        ml_dir = get_ml_base_dir()
        target_dir = ml_dir / "harvested_dataset" / clean_label
        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:6]
        save_filename = f"{timestamp}_{unique_id}.jpg"
        save_path = target_dir / save_filename

        file.save(str(save_path))

        relative_path = f"harvested_dataset/{clean_label}/{save_filename}"
        log_id = MLHarvestLog.create(
            filename=save_filename,
            image_path=relative_path,
            ground_truth_label=ground_truth_label,
            predicted_label=predicted_label,
            predicted_confidence=predicted_confidence,
            uploaded_by=uploaded_by
        )

        return jsonify({
            "message": "Data latih berhasil dikumpulkan",
            "log_id": log_id,
            "filename": save_filename,
            "saved_to": relative_path
        }), 201
    except Exception as e:
        return jsonify({"message": f"Gagal mengumpulkan data latih: {str(e)}"}), 500

@main.route('/api/ml/stats', methods=['GET'])
def get_ml_stats():
    """Mengembalikan statistik data latih yang berhasil dikumpulkan per label."""
    try:
        stats = MLHarvestLog.get_stats()
        return jsonify({"stats": stats}), 200
    except Exception as e:
        return jsonify({"message": f"Gagal mengambil statistik: {str(e)}"}), 500


@main.route('/api/ml/classes', methods=['GET'])
def get_ml_classes():
    """Mengembalikan daftar seluruh kelas / label yang dikenali model saat ini."""
    try:
        ml_dir = get_ml_base_dir()
        labels_file = ml_dir / 'exported_model' / 'labels.txt'
        classes = []
        if labels_file.exists():
            with open(labels_file, 'r', encoding='utf-8') as f:
                classes = [line.strip() for line in f if line.strip()]
        else:
            cleaned_dir = ml_dir / 'cleaned_dataset'
            if cleaned_dir.exists():
                classes = sorted([d.name for d in cleaned_dir.iterdir() if d.is_dir()])
        return jsonify({
            'total_classes': len(classes),
            'classes': classes
        }), 200
    except Exception as e:
        return jsonify({'message': f'Gagal membaca daftar kelas: {str(e)}'}), 500

@main.route('/api/ml/train/trigger', methods=['POST'])
def trigger_ml_retraining():
    """Memicu proses retraining model di server secara asynchronous (background process)."""
    try:
        ml_dir = get_ml_base_dir()
        script_path = ml_dir / 'server_auto_retrain.py'
        venv_python = ml_dir / '.venv' / 'Scripts' / 'python.exe'

        if not script_path.exists():
            return jsonify({'message': 'Skrip server_auto_retrain.py tidak ditemukan di server'}), 404

        python_bin = str(venv_python) if venv_python.exists() else sys.executable

        data = request.get_json(silent=True) or {}
        force = str(data.get('force', request.args.get('force', 'false'))).lower() in ('true', '1')
        epochs = int(data.get('epochs', request.args.get('epochs', 15)))

        cmd = [python_bin, str(script_path), f'--epochs={epochs}']
        if force:
            cmd.append('--force')

        import subprocess
        proc = subprocess.Popen(
            cmd,
            cwd=str(ml_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        return jsonify({
            'message': 'Proses retraining model berhasil dimulai di background server (RTX 2000 Pro)',
            'pid': proc.pid,
            'force': force,
            'epochs': epochs
        }), 202
    except Exception as e:
        return jsonify({'message': f'Gagal memicu retraining: {str(e)}'}), 500


def get_app_release_dir():
    """Mengembalikan direktori penyimpanan berkas rilis APK."""
    # Prioritaskan direktori server jika ada
    server_dir = Path("D:/gudangWarehouse/app_release")
    if server_dir.exists():
        return server_dir
    local_dir = Path(__file__).resolve().parent.parent / "app_release"
    local_dir.mkdir(parents=True, exist_ok=True)
    return local_dir


@main.route('/api/app/version', methods=['GET'])
def get_app_version():
    """Mengembalikan informasi versi aplikasi APK terbaru untuk In-App Self-Update."""
    try:
        release_dir = get_app_release_dir()
        version_file = release_dir / "version.json"
        
        default_info = {
            "latest_version": "1.3.0",
            "version_code": 2,
            "apk_filename": "stats_app_v1.3.0.apk",
            "release_date": "2026-11-11",
            "force_update": False,
            "changelog": "Pembaruan arsitektur model vision ML, optimasi performa & self-update.",
            "apk_size_mb": 0.0
        }
        
        if version_file.exists():
            with open(version_file, 'r', encoding='utf-8') as f:
                info = json.load(f)
        else:
            info = default_info
            with open(version_file, 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2)
                
        base_host = request.host_url.rstrip('/')
        apk_name = info.get("apk_filename", "stats_app_v1.3.0.apk")
        apk_path = release_dir / apk_name
        if apk_path.exists():
            info["apk_size_mb"] = round(apk_path.stat().st_size / (1024 * 1024), 2)
            
        info["apk_download_url"] = f"{base_host}/api/app/download/{apk_name}"
        return jsonify(info), 200
    except Exception as e:
        return jsonify({"message": f"Gagal mengambil versi aplikasi: {str(e)}"}), 500


@main.route('/api/app/download/<filename>', methods=['GET'])
def download_app_apk(filename):
    """Melayani pengunduhan berkas APK aplikasi untuk self-updating."""
    try:
        clean_name = secure_filename(filename)
        release_dir = get_app_release_dir()
        target_path = release_dir / clean_name

        if not target_path.exists():
            return jsonify({"message": f"Berkas APK '{clean_name}' tidak ditemukan di server"}), 404

        return send_from_directory(
            str(release_dir), 
            clean_name, 
            as_attachment=True, 
            mimetype='application/vnd.android.package-archive'
        )
    except Exception as e:
        return jsonify({"message": f"Gagal mengunduh berkas APK: {str(e)}"}), 500

