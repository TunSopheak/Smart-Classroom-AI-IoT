def test_create_student_without_code_generates_next_code(teacher_client, db):
    # Regression: this crashed with NameError (missing `import re`).
    from app.models.academic import ClassGroup
    from app.models.student import Student

    group = db.query(ClassGroup).first()
    assert group is not None

    response = teacher_client.post(
        "/dashboard/class-setup/students/create-and-enroll",
        data={"name": "Auto Code Student", "class_group_id": group.id, "student_code": ""},
        follow_redirects=False,
    )

    assert response.status_code == 303
    student = db.query(Student).filter(Student.name == "Auto Code Student").one()
    assert student.stu_id.startswith("S") and student.stu_id[1:].isdigit()


def test_generated_code_skips_existing_codes(db):
    from app.crud.student_crud import generate_next_student_code
    from app.models.student import Student

    code = generate_next_student_code(db)
    assert db.query(Student).filter(Student.stu_id == code).first() is None
