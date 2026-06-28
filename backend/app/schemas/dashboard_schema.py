from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_students: int = 0
    present: int = 0
    late: int = 0
    absent: int = 0
    permission: int = 0
    active_sessions: int = 0
