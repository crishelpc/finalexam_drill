from flask import Flask, jsonify, request, make_response
from flask_mysqldb import MySQL
from datetime import datetime

app = Flask(__name__)

# MySQL Configuration
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "root"
app.config["MYSQL_DB"] = "hospice_patient_care"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

@app.route("/")
def hello_world():
    return jsonify({"message": "WELCOME TO HOSPICE PATIENT CARE!"})

def validate_patient_input(data):
    required_fields = ['patientFirstName', 'patientLastName', 'patientHomePhone', 'patientEmailAddress']
    for field in required_fields:
        if field not in data or not data[field]:
            return f"'{field}' is required", 400
    return None, None

def validate_admission_input(data):
    required_fields = ['patientID', 'dateOfAdmission', 'dateOfDischarge']
    for field in required_fields:
        if field not in data or not data[field]:
            return f"'{field}' is required", 400
    try:
        datetime.strptime(data["dateOfAdmission"], "%Y-%m-%d")
        datetime.strptime(data["dateOfDischarge"], "%Y-%m-%d")
    except ValueError:
        return "'dateOfAdmission' and 'dateOfDischarge' must be in 'YYYY-MM-DD' format", 400
    return None, None

def data_fetch(query, params=None):
    cur = mysql.connection.cursor()
    cur.execute(query, params)
    result = cur.fetchall()
    cur.close()
    return result

@app.route("/patients", methods=["GET"])
def get_patients():
    data = data_fetch("""SELECT * FROM patients""")
    return make_response(jsonify(data), 200)

@app.route("/patientadmissions/<int:patient_id>", methods=["GET"])
def get_patient_admission(patient_id):
    data = data_fetch("""SELECT * FROM PatientAdmissions WHERE patientID = %s""", (patient_id,))
    if not data:
        return make_response(
            jsonify(
                {
                    "error": "Admission not found for the given patient"
                }
            ), 
            404)
    return make_response(jsonify(data), 200)

@app.route("/healthprofessionals/<int:staff_id>/patients", methods=["GET"])
def get_patients_info(staff_id):
    data = data_fetch("""
        SELECT DISTINCT Patients.patientID, Patients.patientFirstName, Patients.patientLastName, 
                        Patients.patientHomePhone, Patients.patientEmailAddress
        FROM Treatments
        JOIN Patients ON Treatments.patientID = Patients.patientID
        WHERE Treatments.staffID = %s
    """, (staff_id,))

    if not data:
        return make_response(jsonify({"error": "No patients found for this health professional"}), 404)

    return make_response(jsonify(data), 200)

@app.route("/treatments/<int:patient_id>", methods=["GET"])
def get_treatment_history(patient_id):
    data = data_fetch("""SELECT treatmentID, treatmentDescription, treatmentStatus
        FROM Treatments WHERE patientID = %s""", (patient_id,))
    return make_response(jsonify(data), 200)

@app.route("/patients", methods=["POST"])
def add_patient():
    data = request.get_json()
    error_message, status_code = validate_patient_input(data)
    if error_message:
        return jsonify({"error": error_message}), status_code

    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO Patients (patientFirstName, patientLastName, patientHomePhone, patientEmailAddress) VALUES (%s, %s, %s, %s)",
            (data['patientFirstName'], data['patientLastName'], data['patientHomePhone'], data['patientEmailAddress'])
        )
        mysql.connection.commit()
        cursor.close()
        return jsonify({"message": "Patient added successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/patientadmissions", methods=["POST"])
def add_admission():
    info = request.get_json()
    error_message, status_code = validate_admission_input(info)
    if error_message:
        return jsonify({"error": error_message}), status_code

    try:
        cur = mysql.connection.cursor()
        cur.execute(
            """INSERT INTO PatientAdmissions (patientID, dateOfAdmission, dateOfDischarge)
            VALUES (%s, %s, %s)""",
            (info["patientID"], info["dateOfAdmission"], info["dateOfDischarge"])
        )
        mysql.connection.commit()
        rows_affected = cur.rowcount
        cur.close()
        return make_response(
            jsonify(
                {"message": "Admission added successfully", "rows_affected": rows_affected}
            ),
            201,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/treatments/<int:treatment_id>", methods=["PUT"])
def update_treatment(treatment_id):
    info = request.get_json()
    treatmentStatus = info.get("treatmentStatus")
    if not treatmentStatus:
        return jsonify({"error": "'treatmentStatus' is required"}), 400

    try:
        cur = mysql.connection.cursor()
        cur.execute(
            """UPDATE Treatments SET treatmentStatus = %s WHERE treatmentID = %s""",
            (treatmentStatus, treatment_id),
        )
        mysql.connection.commit()
        rows_affected = cur.rowcount
        cur.close()
        return make_response(
            jsonify(
                {"message": "Patient treatment status updated successfully", "rows_affected": rows_affected}
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/patients/<int:patient_id>', methods=['DELETE'])
def delete_patient(patient_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("""DELETE FROM Patients WHERE patientID = %s""", (patient_id,))
        mysql.connection.commit()
        rows_affected = cur.rowcount
        cur.close()
        return make_response(
            jsonify(
                {"message": "Patient record deleted successfully", "rows_affected": rows_affected}
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/treatments/<int:treatment_id>', methods=['DELETE'])
def delete_treatment(treatment_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("""DELETE FROM Treatments WHERE treatmentID = %s""", (treatment_id,))
        mysql.connection.commit()
        rows_affected = cur.rowcount
        cur.close()
        return make_response(
            jsonify(
                {"message": "Treatment record deleted successfully", "rows_affected": rows_affected}
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not Found", "message": str(error)}), 404

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad Request", "message": str(error)}), 400

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal Server Error", "message": "Something went wrong on the server."}), 500

if __name__ == "__main__":
    app.run(debug=True)