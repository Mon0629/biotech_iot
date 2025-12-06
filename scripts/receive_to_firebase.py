from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, db
import time

app = Flask(__name__)

# Firebase setup
cred = credentials.Certificate("/home/biotech/biotech_iot/firebase-key.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://hydronew-iot-default-rtdb.asia-southeast1.firebasedatabase.app/"
})

@app.route('/sensordata', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data received"}), 400

        turbidity = data.get("turbidity")
        ph = data.get("ph")
        tds = data.get("tds")
        status = data.get("status")

        print("\nReceived from ESP32:")
        print(f"  Turbidity: {turbidity} NTU")
        print(f"  pH: {ph}")
        print(f"  TDS: {tds} ppm")
        print(f"  Status: {status}")

        # Upload to Firebase
        ref = db.reference("sensorData")
        ref.push({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "turbidity": turbidity,
            "ph": ph,
            "tds": tds,
            "status": status
        })

        return jsonify({"message": "Data stored successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
