# -*- coding: utf-8 -*-
"""Append manual test data without deleting existing records."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path
from sqlalchemy import inspect, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from core.security import hash_password
from database.connection import SessionLocal, engine
from database.models.class_ import Class
from database.models.school_rule import SchoolRule
from database.models.score import Score
from database.models.student import Student
from database.models.teacher import Teacher
from database.models.user import User


def ensure_user(db, username: str, password: str, role: str, name: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if user:
        return user
    user = User(username=username, password_hash=hash_password(password), role=role, name=name)
    db.add(user)
    db.flush()
    return user


def ensure_teacher(db, name: str, subject: str, title: str, class_ids: str | None) -> Teacher:
    teacher = db.query(Teacher).filter(Teacher.name == name).first()
    if teacher:
        teacher.subject = subject
        teacher.title = title
        teacher.class_ids = class_ids
        db.flush()
        return teacher
    teacher = Teacher(name=name, subject=subject, title=title, class_ids=class_ids)
    db.add(teacher)
    db.flush()
    return teacher


def ensure_class(db, grade: str, name: str, head_teacher_id: int | None, max_count: int, status: int) -> Class:
    class_obj = db.query(Class).filter(Class.name == name).first()
    if class_obj:
        class_obj.grade = grade
        class_obj.head_teacher_id = head_teacher_id
        class_obj.max_count = max_count
        class_obj.status = status
        db.flush()
        return class_obj
    class_obj = Class(
        grade=grade,
        name=name,
        head_teacher_id=head_teacher_id,
        max_count=max_count,
        current_count=0,
        status=status,
    )
    db.add(class_obj)
    db.flush()
    return class_obj


def ensure_student(
    db,
    student_no: str,
    name: str,
    gender: str,
    age: int,
    grade: str,
    class_id: int | None,
    contact: str | None,
    specialty: str | None,
    tags: str | None,
) -> Student:
    student = db.query(Student).filter(Student.student_no == student_no).first()
    if student:
        student.name = name
        student.gender = gender
        student.age = age
        student.grade = grade
        student.class_id = class_id
        student.contact = contact
        student.specialty = specialty
        student.tags = tags
        db.flush()
        return student
    student = Student(
        student_no=student_no,
        name=name,
        gender=gender,
        age=age,
        grade=grade,
        class_id=class_id,
        contact=contact,
        specialty=specialty,
        tags=tags,
    )
    db.add(student)
    db.flush()
    return student


def ensure_score(db, student_id: int, class_id: int, exam_batch: str, subject: str, score: float) -> Score:
    score_obj = (
        db.query(Score)
        .filter(
            Score.student_id == student_id,
            Score.class_id == class_id,
            Score.exam_batch == exam_batch,
            Score.subject == subject,
        )
        .first()
    )
    if score_obj:
        score_obj.score = Decimal(str(score))
        db.flush()
        return score_obj
    score_obj = Score(
        student_id=student_id,
        class_id=class_id,
        exam_batch=exam_batch,
        subject=subject,
        score=Decimal(str(score)),
    )
    db.add(score_obj)
    db.flush()
    return score_obj


def ensure_rule(db, category: str, title: str, content: str, updated_by: int | None) -> SchoolRule:
    rule = db.query(SchoolRule).filter(SchoolRule.title == title).first()
    if rule:
        rule.category = category
        rule.content = content
        rule.updated_by = updated_by
        db.flush()
        return rule
    rule = SchoolRule(category=category, title=title, content=content, updated_by=updated_by)
    db.add(rule)
    db.flush()
    return rule


def sync_class_counts(db) -> None:
    for class_obj in db.query(Class).all():
        class_obj.current_count = db.query(Student).filter(Student.class_id == class_obj.id).count()
    db.flush()


def score_value(student_no: str, subject: str, exam_batch: str) -> float:
    base = sum(ord(ch) for ch in (student_no + subject + exam_batch))
    return round(62 + (base % 35) + ((base // 7) % 10) / 10, 1)


def main() -> None:
    db = SessionLocal()
    try:
        ensure_student_grade_column()
        admin = db.query(User).filter(User.username == "admin").first()

        ensure_user(db, "zhou_physics", "teacher123", "teacher", "周美玲")
        ensure_user(db, "sun_pe", "teacher123", "teacher", "孙大海")
        teacher_wang = ensure_teacher(db, "王建国", "数学", "head_teacher", "1")
        teacher_liu = ensure_teacher(db, "刘芳华", "语文", "head_teacher", "2")
        teacher_chen = ensure_teacher(db, "陈志远", "英语", "head_teacher", "4")
        ensure_teacher(db, "周美玲", "物理", "normal", "1,2,3,6")
        ensure_teacher(db, "孙大海", "体育", "normal", "1,2,3,4,6")

        class_1 = ensure_class(db, "2024级", "2024级1班", teacher_wang.id, 50, 1)
        class_2 = ensure_class(db, "2024级", "2024级2班", teacher_liu.id, 50, 1)
        class_3 = ensure_class(db, "2024级", "2024级3班", None, 50, 1)
        class_4 = ensure_class(db, "2023级", "2023级1班", teacher_chen.id, 45, 1)
        ensure_class(db, "2022级", "2022级1班", None, 48, 0)
        class_6 = ensure_class(db, "2024级", "2024级4班", None, 50, 1)

        student_specs = [
            ("202400103", "陈晨", "female", 15, "2024级", class_1.id, "13800000003", "绘画", "心理关爱,班干部"),
            ("202400104", "孙浩", "male", 16, "2024级", class_1.id, "13800000004", "篮球", "体育特长"),
            ("202400105", "何雨彤", "female", 15, "2024级", class_1.id, "13800000005", "主持", "英语拔尖"),
            ("202400203", "周子轩", "male", 16, "2024级", class_2.id, "13800000006", "编程", "数学拔尖"),
            ("202400204", "杨可欣", "female", 15, "2024级", class_2.id, "13800000007", "朗诵", "英语拔尖"),
            ("202400205", "吴思雨", "female", 15, "2024级", class_2.id, None, "钢琴", "学困生"),
            ("202400302", "郑凯", "male", 16, "2024级", class_3.id, "13800000008", "足球", "物理特长"),
            ("202400303", "许梦瑶", "female", 15, "2024级", class_3.id, "13800000009", "舞蹈", "心理关爱"),
            ("202400304", "马一鸣", "male", 16, "2024级", class_3.id, "13800000010", "围棋", "迟到"),
            ("202300101", "高志远", "male", 17, "2023级", class_4.id, "13800000011", "篮球", "班干部"),
            ("202300102", "林嘉怡", "female", 17, "2023级", class_4.id, "13800000012", "声乐", "英语拔尖"),
            ("202400401", "唐子墨", "male", 15, "2024级", None, "13800000013", "编程", "待分班"),
            ("202400402", "宋雨晴", "female", 15, "2024级", None, "13800000014", "书法", "待分班"),
            ("202400403", "彭宇航", "male", 15, "2024级", None, "13800000015", "乒乓球", "待分班"),
            ("202400404", "罗欣怡", "female", 15, "2024级", None, "13800000016", "钢琴", "待分班"),
            ("202400405", "贺俊杰", "male", 15, "2024级", None, "13800000017", "足球", "待分班"),
            ("202400406", "蔡可人", "female", 15, "2024级", None, "13800000018", "绘画", "待分班"),
            ("202400407", "段星宇", "male", 15, "2024级", class_6.id, "13800000019", "机器人", "信息技术特长"),
            ("202400408", "顾安然", "female", 15, "2024级", class_6.id, "13800000020", "朗读", "班干部"),
        ]
        for spec in student_specs:
            ensure_student(db, *spec)

        ensure_user(db, "stu_202400103", "student123", "student", "陈晨")
        ensure_user(db, "stu_202400204", "student123", "student", "杨可欣")
        ensure_user(db, "stu_202300101", "student123", "student", "高志远")

        batches = ["期中考试", "期末考试", "月考"]
        subjects = ["语文", "数学", "英语", "物理"]
        classed_students = db.query(Student).filter(Student.class_id.is_not(None)).all()
        for student in classed_students:
            for batch in batches:
                chosen_subjects = subjects if student.class_id in {class_3.id, class_4.id, class_6.id} else subjects[:3]
                for subject in chosen_subjects:
                    ensure_score(db, student.id, student.class_id, batch, subject, score_value(student.student_no, subject, batch))

        updated_by = admin.id if admin else None
        ensure_rule(
            db,
            "行为规范",
            "手机管理",
            "学生在教学时段未经允许使用手机的，由班主任或年级组暂存保管。首次违规由家长在当周周五17:00后到校领取；再次违规须由家长到校与班主任面谈后领取，并取消下一周携带手机入校资格。",
            updated_by,
        )
        ensure_rule(
            db,
            "考勤",
            "请假管理",
            "学生请假须由家长提前向班主任说明原因。病假需补交相关证明，事假原则上应在请假前完成审批，返校后当天完成销假登记。",
            updated_by,
        )
        ensure_rule(
            db,
            "宿舍管理",
            "宿舍晚归与熄灯",
            "住宿生须在21:20前返回宿舍，21:40后保持安静，22:00准时熄灯。无故晚归两次以上将通知家长并记入德育考核。",
            updated_by,
        )

        sync_class_counts(db)
        db.commit()

        print("manual test data appended successfully")
        print("users:", db.query(User).count())
        print("teachers:", db.query(Teacher).count())
        print("classes:", db.query(Class).count())
        print("students:", db.query(Student).count())
        print("scores:", db.query(Score).count())
        print("school_rules:", db.query(SchoolRule).count())
    finally:
        db.close()


def ensure_student_grade_column() -> None:
    inspector = inspect(engine)
    column_names = {column["name"] for column in inspector.get_columns("student")}

    with engine.begin() as connection:
        if "grade" not in column_names:
            if engine.dialect.name == "mysql":
                connection.execute(text("ALTER TABLE student ADD COLUMN grade VARCHAR(20) NULL COMMENT '年级'"))
            else:
                connection.execute(text("ALTER TABLE student ADD COLUMN grade VARCHAR(20)"))

        if engine.dialect.name == "mysql":
            connection.execute(
                text(
                    """
                    UPDATE student s
                    LEFT JOIN class c ON s.class_id = c.id
                    SET s.grade = COALESCE(s.grade, c.grade)
                    WHERE s.grade IS NULL AND s.class_id IS NOT NULL
                    """
                )
            )
            connection.execute(
                text(
                    """
                    UPDATE student
                    SET grade = CONCAT(SUBSTRING(student_no, 1, 4), '级')
                    WHERE grade IS NULL
                      AND student_no IS NOT NULL
                      AND CHAR_LENGTH(student_no) >= 4
                    """
                )
            )


if __name__ == "__main__":
    main()
