import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
from app import create_app
from app.models import Tool

def test_tipe_functionality():
    app = create_app()
    client = app.test_client()

    print("=== TEST 1: GET ALL BARANG ===")
    res_all = client.get('/get_barang')
    assert res_all.status_code == 200
    all_data = res_all.get_json()
    print(f"Total all items: {len(all_data)}")
    for item in all_data[:3]:
        print(f" - {item['nama_barang']} ({item.get('tipe')})")

    print("\n=== TEST 2: GET ONLY TOOLS ===")
    res_tools = client.get('/get_barang?tipe=tool')
    assert res_tools.status_code == 200
    tools_data = res_tools.get_json()
    print(f"Total tools: {len(tools_data)}")
    for item in tools_data:
        assert item.get('tipe') == 'tool', f"Expected tool, got {item.get('tipe')}"
        print(f" - [TOOL] {item['nama_barang']} (qty: {item['jumlah']})")

    print("\n=== TEST 3: GET ONLY MATERIALS ===")
    res_materials = client.get('/get_barang?tipe=material')
    assert res_materials.status_code == 200
    materials_data = res_materials.get_json()
    print(f"Total materials: {len(materials_data)}")
    for item in materials_data:
        assert item.get('tipe') == 'material', f"Expected material, got {item.get('tipe')}"
        print(f" - [MATERIAL] {item['nama_barang']} (qty: {item['jumlah']})")

    print("\n=== TEST 4: ADD BARANG WITH TIPE ===")
    test_tool_payload = {
        "nama_barang": "Tang Kombinasi Knipex 02 02 200",
        "jumlah": 5,
        "lemari": "Lemari A3",
        "lokasi": "Bengkel K&I",
        "username": "tester",
        "tipe": "tool"
    }
    res_add = client.post('/add_barang', json=test_tool_payload)
    assert res_add.status_code == 200
    print(f"Add tool response: {res_add.get_json()}")

    # Verify added tool is in tools
    res_check = client.get('/get_barang?tipe=tool')
    names = [i['nama_barang'] for i in res_check.get_json()]
    assert "Tang Kombinasi Knipex 02 02 200" in names
    print(" Verified new tool appears in ?tipe=tool")

    # Clean up test tool
    with app.app_context():
        Tool.delete("Tang Kombinasi Knipex 02 02 200", "Lemari A3", "Bengkel K&I")
    print(" Verified cleanup.")

    print("\n[SUCCESS] ALL BACKEND TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_tipe_functionality()
