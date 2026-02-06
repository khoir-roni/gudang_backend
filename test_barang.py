import requests
import json
import logging

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Flask App URL ---
BASE_URL = "http://127.0.0.1:5000"

def test_add_barang():
    """
    Test menambah barang baru dengan nama 'coba', lokasi 'coba', jumlah 1
    """
    logging.info("=" * 60)
    logging.info("TEST 1: Menambah Barang Baru")
    logging.info("=" * 60)
    
    payload = {
        "nama_barang": "coba",
        "jumlah": 1,
        "lemari": "A1",
        "lokasi": "coba",
        "username": "admin"
    }
    
    logging.info(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(f"{BASE_URL}/add_barang", json=payload)
        logging.info(f"Status Code: {response.status_code}")
        logging.info(f"Response: {response.json()}")
        
        if response.status_code == 200:
            logging.info("✅ Barang berhasil ditambahkan!")
        else:
            logging.error("❌ Gagal menambah barang!")
        
        return response.status_code == 200
        
    except Exception as e:
        logging.error(f"❌ Error: {e}")
        return False

def test_get_barang():
    """
    Test mengambil daftar semua barang
    """
    logging.info("=" * 60)
    logging.info("TEST 2: Mengambil Daftar Barang")
    logging.info("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/get_barang")
        logging.info(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            barang_list = response.json()
            logging.info(f"Total barang: {len(barang_list)}")
            logging.info(f"Data barang: {json.dumps(barang_list, indent=2)}")
            logging.info("✅ Berhasil mengambil daftar barang!")
            return True
        else:
            logging.error("❌ Gagal mengambil daftar barang!")
            return False
            
    except Exception as e:
        logging.error(f"❌ Error: {e}")
        return False

def test_update_barang():
    """
    Test mengambil/mengurangi barang (ambil 1 barang 'coba')
    """
    logging.info("=" * 60)
    logging.info("TEST 3: Mengambil Barang (Kurangi Stok)")
    logging.info("=" * 60)
    
    payload = {
        "nama_barang": "coba",
        "jumlah": 1,
        "lemari": "A1",
        "lokasi": "coba",
        "username": "admin"
    }
    
    logging.info(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(f"{BASE_URL}/update_barang", json=payload)
        logging.info(f"Status Code: {response.status_code}")
        logging.info(f"Response: {response.json()}")
        
        if response.status_code == 200:
            logging.info("✅ Barang berhasil diambil!")
        else:
            logging.error("❌ Gagal mengambil barang!")
        
        return response.status_code == 200
        
    except Exception as e:
        logging.error(f"❌ Error: {e}")
        return False

def main():
    logging.info("🚀 MEMULAI TEST BARANG")
    logging.info(f"Base URL: {BASE_URL}")
    logging.info("")
    
    results = []
    
    # Test 1: Tambah barang
    results.append(("Tambah Barang", test_add_barang()))
    logging.info("")
    
    # Test 2: Lihat daftar barang
    results.append(("Lihat Daftar Barang", test_get_barang()))
    logging.info("")
    
    # Test 3: Ambil barang
    results.append(("Ambil Barang", test_update_barang()))
    logging.info("")
    
    # Test 4: Lihat daftar barang lagi (stok sudah berkurang)
    results.append(("Lihat Daftar Barang (After Update)", test_get_barang()))
    logging.info("")
    
    # --- Summary ---
    logging.info("=" * 60)
    logging.info("📊 RINGKASAN HASIL TEST")
    logging.info("=" * 60)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logging.info(f"{test_name}: {status}")
    logging.info("=" * 60)

if __name__ == '__main__':
    main()
