from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, BigInteger, Float, DateTime, JSON
from database import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    area = Column(String, nullable=False)
    prefecture = Column(String, nullable=False)
    property_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    excerpt = Column(Text, nullable=True)
    meta_title = Column(String, nullable=True)
    meta_description = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)
    structured_data = Column(JSON, nullable=True)
    status = Column(String, default="published")
    generated_by = Column(String, default="gemini")
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    status = Column(String, nullable=False)  # running / success / error
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prefecture = Column(String, nullable=False)
    municipality = Column(String, nullable=False)
    district = Column(String, nullable=True)
    trade_price = Column(BigInteger, nullable=True)
    price_per_unit = Column(Integer, nullable=True)
    area = Column(Float, nullable=True)
    floor_plan = Column(String, nullable=True)
    building_year = Column(String, nullable=True)
    structure = Column(String, nullable=True)
    trade_period = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
