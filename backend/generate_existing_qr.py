from app.database.database import SessionLocal
from app.crud.student_crud import get_students
from app.services.qr_service import build_student_qr_code, generate_student_qr_image

db = SessionLocal()
try:
    students = get_students(db)
    for student in students:
        if not student.qr_code:
            student.qr_code = build_student_qr_code(student.stu_id)
        student.qr_image_path = generate_student_qr_image(student.stu_id, student.qr_code)
        print(f"Generated QR for {student.stu_id}: {student.qr_image_path}")
    db.commit()
    print(f"Done. Generated/refreshed QR images for {len(students)} students.")
finally:
    db.close()
