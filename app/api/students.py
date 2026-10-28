import csv
import io
from flask import request, jsonify
from app.api import api_bp
from app.extensions import db
from app.models.student import Student
from app.utils.validators import validate_student_data
from app.utils.security import log_audit_event

@api_bp.route("/students", methods=["GET"])
def list_students():
    """List registered students with search and batch filtering."""
    search = request.args.get("search", "").strip()
    batch = request.args.get("batch", "").strip()
    status = request.args.get("status", "").strip()

    query = Student.query
    if search:
        query = query.filter((Student.name.ilike(f"%{search}%")) | (Student.student_id.ilike(f"%{search}%")))
    if batch:
        query = query.filter_by(batch=batch)
    if status:
        query = query.filter_by(enrollment_status=status)

    students = query.order_by(Student.name.asc()).all()
    return jsonify({
        "count": len(students),
        "students": [s.to_dict() for s in students],
    }), 200

@api_bp.route("/students", methods=["POST"])
def create_student():
    """Add a new student record."""
    data = request.get_json() or {}
    is_valid, errors = validate_student_data(data)
    if not is_valid:
        return jsonify({"errors": errors}), 400

    # Check student_id uniqueness
    existing = Student.query.filter_by(student_id=data["student_id"]).first()
    if existing:
        return jsonify({"error": f"Student ID '{data['student_id']}' already exists."}), 409

    student = Student(
        student_id=data["student_id"],
        name=data["name"],
        email=data.get("email"),
        batch=data.get("batch", "Default Batch"),
        enrollment_status=data.get("enrollment_status", "active"),
        consent_given=data.get("consent_given", True),
    )
    db.session.add(student)
    db.session.commit()
    log_audit_event("CREATE_STUDENT", "student", student.id, f"Added student {student.name} ({student.student_id})")

    return jsonify({"message": "Student created successfully", "student": student.to_dict()}), 201

@api_bp.route("/students/<int:student_id>", methods=["PUT"])
def update_student(student_id: int):
    """Update student record details or deactivate."""
    student = db.session.get(Student, student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    data = request.get_json() or {}
    if "name" in data and data["name"].strip():
        student.name = data["name"].strip()
    if "email" in data:
        student.email = data["email"].strip()
    if "batch" in data and data["batch"].strip():
        student.batch = data["batch"].strip()
    if "enrollment_status" in data:
        student.enrollment_status = data["enrollment_status"]
    if "consent_given" in data:
        student.consent_given = bool(data["consent_given"])

    db.session.commit()
    log_audit_event("UPDATE_STUDENT", "student", student.id, f"Updated student {student.name}")
    return jsonify({"message": "Student updated", "student": student.to_dict()}), 200

@api_bp.route("/students/import_csv", methods=["POST"])
def import_students_csv():
    """Bulk import students via CSV upload."""
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if not file.filename.endswith(".csv"):
        return jsonify({"error": "File must be a .csv"}), 400

    stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
    reader = csv.DictReader(stream)
    
    imported = 0
    skipped = 0
    for row in reader:
        s_id = row.get("student_id") or row.get("roll_no") or row.get("id")
        name = row.get("name") or row.get("full_name")
        email = row.get("email")
        batch = row.get("batch") or "Default Batch"

        if s_id and name:
            s_id = s_id.strip()
            name = name.strip()
            existing = Student.query.filter_by(student_id=s_id).first()
            if not existing:
                st = Student(
                    student_id=s_id,
                    name=name,
                    email=email.strip() if email else None,
                    batch=batch.strip() if batch else "Default Batch",
                    consent_given=True,
                )
                db.session.add(st)
                imported += 1
            else:
                skipped += 1

    db.session.commit()
    log_audit_event("IMPORT_STUDENTS", "student", None, f"Imported {imported} students, skipped {skipped} duplicates")
    return jsonify({
        "message": f"Successfully imported {imported} students ({skipped} skipped duplicates)",
        "imported": imported,
        "skipped": skipped,
    }), 200
