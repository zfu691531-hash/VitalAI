# -*- coding: utf-8 -*-
"""
成绩波动诊断工具
================
分析学生成绩变化趋势，给出诊断建议。
"""

from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models.user import User
from database.models.student import Student
from database.models.score import Score
from services.ai.base import ai_client, save_history
from services.user_service import get_student_by_user_id
from core.response import success_response, error_response
from utils.logger import logger


class ScoreDiagnosisRequest(BaseModel):
    """成绩诊断请求"""
    student_id: Optional[int] = Field(None, description="学生ID（不填则查当前用户）")
    subject: Optional[str] = Field(None, description="科目（不填则分析全部）")


async def diagnose_score(
    db: Session,
    current_user: User,
    request: ScoreDiagnosisRequest,
) -> dict:
    """
    诊断成绩波动
    
    Args:
        db: 数据库会话
        current_user: 当前用户
        request: 请求参数
    
    Returns:
        dict: 诊断结果
    """
    # 获取学生ID
    student_id = request.student_id
    if not student_id:
        student = get_student_by_user_id(db, current_user.id)
        if not student:
            return error_response(msg="未找到关联学生信息")
        student_id = student.id
    
    # 查询学生信息
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return error_response(msg="学生不存在")
    
    # 查询成绩历史
    query = db.query(Score).filter(Score.student_id == student_id)
    if request.subject:
        query = query.filter(Score.subject == request.subject)
    
    scores = query.order_by(Score.created_at).all()
    
    if not scores:
        return success_response(data={"diagnosis": "暂无成绩记录，无法分析"})
    
    # 构建成绩数据
    score_data = []
    subject_scores = {}  # 按科目分组
    
    for s in scores:
        score_data.append({
            "exam_batch": s.exam_batch,
            "subject": s.subject,
            "score": float(s.score),
            "date": str(s.created_at.date()),
        })
        
        if s.subject not in subject_scores:
            subject_scores[s.subject] = []
        subject_scores[s.subject].append(float(s.score))
    
    # 计算各科目平均分和趋势
    subject_analysis = []
    for subject, score_list in subject_scores.items():
        avg = sum(score_list) / len(score_list)
        trend = "稳定"
        if len(score_list) >= 2:
            diff = score_list[-1] - score_list[0]
            if diff > 5:
                trend = "上升"
            elif diff < -5:
                trend = "下降"
        
        subject_analysis.append(
            f"- {subject}：平均{avg:.1f}分，趋势{trend}（最近{len(score_list)}次：{'→'.join(map(str, score_list[-5:]))}）"
        )
    
    system_prompt = """你是一位资深的学业分析师。
请根据学生的成绩数据进行分析诊断，给出专业的学业建议。

要求：
1. 分析成绩变化趋势
2. 找出优势科目和薄弱科目
3. 给出针对性的改进建议
4. 语言鼓励为主，指出问题时要有建设性
5. 字数200-300字"""

    user_prompt = f"""学生：{student.name}
成绩分析数据：
{chr(10).join(subject_analysis)}

详细成绩记录：
{chr(10).join([f"- {s['exam_batch']} {s['subject']}: {s['score']}分" for s in score_data[-10:]])}

请给出诊断分析："""

    result = await ai_client.call(system_prompt, user_prompt)
    
    # 保存历史
    save_history(
        db=db,
        user_id=current_user.id,
        tool_type="score_diag",
        input_params=request.model_dump(),
        content=result,
        student_id=student_id,
    )
    
    return success_response(data={
        "diagnosis": result,
        "score_data": score_data,
        "subject_analysis": subject_analysis,
    })
