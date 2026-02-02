from flask import Blueprint, request, jsonify
from .models import Tool, History, User
import bcrypt

main = Blueprint('main', __name__)

@main.route('/add_barang', methods=['POST'])
def add_barang():
    data = request.get_json()
    try:
        Tool.create(**data)
        return jsonify({"message": "Barang berhasil ditambahkan!"})
    except Exception as e:
        return jsonify({"message": f"Error: {e}"}), 500

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
    try:
        result = Tool.update_stock(**data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"message": f"Error: {e}"}), 500

@main.route('/delete_barang', methods=['DELETE'])
def delete_barang():
    data = request.get_json()
    try:
        Tool.delete(**data)
        return jsonify({"message": "Barang berhasil dihapus!"})
    except Exception as e:
        return jsonify({"message": "Error deleting barang"}), 500

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
