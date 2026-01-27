from __future__ import annotations

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, DateTime, Integer, String, Text, JSON
from sqlalchemy.sql import func

Base = declarative_base()


class N8nFilaMensagens(Base):
    __tablename__ = "n8n_fila_mensagens"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True)
    id_mensagem = Column(String, nullable=False)
    telefone = Column(String, nullable=False)
    mensagem = Column(Text)
    timestamp = Column(DateTime(timezone=True))
    client_id = Column(String)
    trace_id = Column(String)
    message_id = Column(String)
    remote_jid = Column(String)
    message_type = Column(String)
    status = Column(String, default="pending")
    locked_at = Column(DateTime(timezone=True))
    locked_by = Column(String)
    processed_at = Column(DateTime(timezone=True))
    error = Column(Text)


class ActiveSession(Base):
    __tablename__ = "active_sessions"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True)
    session_id = Column(String, unique=True, nullable=False)
    last_message = Column(Text)
    last_message_type = Column(String)
    last_message_id = Column(String)
    status = Column(String, default="active")
    followup_sent_at = Column(DateTime(timezone=True))
    followup_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True)
    order_id = Column(String, unique=True, nullable=False)
    telefone = Column(String)
    status = Column(String)
    cod_store = Column(String)
    payload = Column(JSON)
    response = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SaiposMenuRaw(Base):
    __tablename__ = "saipos_menu_raw"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True)
    client_id = Column(String)
    tipo = Column(String)
    categoria = Column(String)
    tamanho = Column(String)
    id_store_item = Column(Integer)
    item = Column(String)
    id_store_choice = Column(Integer)
    complemento = Column(String)
    complemento_item = Column(String)
    price = Column(String)
    codigo_saipos = Column(String)
    store_item_enabled = Column(String)
    store_choice_enabled = Column(String)
    store_choice_item_enabled = Column(String)
    item_type = Column(String)
    pdv_code = Column(String)
    parent_pdv_code = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
