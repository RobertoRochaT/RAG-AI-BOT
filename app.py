import os
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from embed import embed
from query import query
from flask_cors import CORS,cross_origin

# Cargar variables de entorno
load_dotenv()

# Configuración de la carpeta temporal
TEMP_FOLDER = os.getenv('TEMP_FOLDER', './_temp')
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Configuración de Flask y MongoDB
app = Flask(__name__)
cors = CORS(app) # enable cors for all domains and all routes (this is insecure)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config["MONGO_URI"] = "mongodb+srv://Rocha:3CM3niSeTasVK9ND@cluster0.cw6gz.mongodb.net/chatbotlaguna?retryWrites=true&w=majority" # Usa variables de entorno para seguridad
mongo = PyMongo(app)

@app.route('/embed', methods=['POST'])
def route_embed():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        embedded = embed(file)
        if embedded:
            return jsonify({"message": "File embedded successfully"}), 200
        return jsonify({"error": "File embedding failed"}), 500
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/querys', methods=['GET'])
@cross_origin()
def get_queries():
    try:
        conversation_name = request.args.get('conversation_name')  # Obtener filtro opcional

        # Si se proporciona un nombre de conversación, filtrar por él
        filter_query = {"Conversation name": conversation_name} if conversation_name else {}

        # Obtener todas las consultas de la base de datos
        consultas = list(mongo.db.consultas.find(filter_query, {"_id": 0}))  # Excluye el _id de MongoDB

        return jsonify({"queries": consultas}), 200

    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route('/query', methods=['POST'])
def route_query():
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "Query is required"}), 400

    user_query = data["query"]
    now = datetime.now()
    consulta = {
        "Date": now.strftime("%Y-%m-%d"),
        "Time": now.strftime("%H:%M:%S"),
        "Conversation name": data.get("conversation_name", "Default Conversation"),
        "Query": user_query,
        "Status": "Processing"
    }

    try:
        inserted_doc = mongo.db.consultas.insert_one(consulta)
        consulta_id = inserted_doc.inserted_id

        response = query(user_query)

        if response:
            mongo.db.consultas.update_one(
                {"_id": consulta_id},
                {"$set": {"Status": "Success", "Response": response}}
            )
            return jsonify({"message": response}), 200

        # Si la consulta falla, actualizar el estado
        mongo.db.consultas.update_one(
            {"_id": consulta_id},
            {"$set": {"Status": "Failed"}}
        )
        return jsonify({"error": "Something went wrong"}), 500

    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
        
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)
