from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, BigInteger, Float, DateTime, JSON, Date, UniqueConstraint
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
    article_type = Column(String, default="area")        # area / guide / qa / ranking
    status = Column(String, default="published")
    generated_by = Column(String, default="gemini")
    duration_ms = Column(Integer, nullable=True)
    published_at = Column(DateTime, nullable=True)  # Hugo/GitHub Pages 公開日時
    last_optimized_at = Column(DateTime, nullable=True)  # 最後に最適化された日時
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


# ─────────────────────────────────────────────────────────────────────────────
# OpenClaw Phase 1: 自律エージェント用テーブル
# ─────────────────────────────────────────────────────────────────────────────

class TopicQueue(Base):
    """
    記事生成トピックキュー
    - 静的なARTICLE_TOPICSリストを置き換え
    - Commander Agentが優先度順に選択して処理
    - status管理で重複記事を防止（リスク対策）
    """
    __tablename__ = "topic_queue"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    # コンテンツ分類
    article_type  = Column(String, nullable=False, default="area")
    # area / guide / qa / ranking / news / data
    category      = Column(String, nullable=True)
    # mortgage / rent / investment / policy / area / tax / buying / selling / stats
    # 地域情報（area/ranking型で使用）
    prefecture    = Column(String, nullable=True)
    area          = Column(String, nullable=True)
    property_type = Column(String, nullable=True)
    # 記事ヒント
    title_hint    = Column(Text, nullable=True)   # AIへの執筆ヒント
    keywords      = Column(JSON, nullable=True)
    # 優先度管理（Commander Agentが制御）
    priority      = Column(Integer, default=50)   # 0-100、高いほど先に処理
    # ステータス管理（重複防止リスク対策）
    status        = Column(String, default="pending")
    # pending / generating / done / skip / error
    error_count   = Column(Integer, default=0)    # エラー回数（3回でskip）
    # 関連データ
    knowledge_ids = Column(JSON, nullable=True)   # knowledge_base.id リスト
    article_slug  = Column(String, nullable=True) # 生成後のarticle.slug
    # タイムスタンプ
    created_at    = Column(DateTime, default=datetime.utcnow)
    generated_at  = Column(DateTime, nullable=True)


class KnowledgeBase(Base):
    """
    構造化知識データベース
    - Research Agentが収集したデータを格納
    - Writer Agentが記事生成時に参照
    - 有効期限管理でデータ陳腐化リスクを防止
    """
    __tablename__ = "knowledge_base"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    # 分類
    category    = Column(String, nullable=False)
    # mortgage_rate / rent_stats / price_stats / policy / area_info / tax / population
    subcategory = Column(String, nullable=True)
    scope       = Column(String, nullable=True)   # national / prefecture / city
    prefecture  = Column(String, nullable=True)
    # データ本体
    title       = Column(Text, nullable=False)
    summary     = Column(Text, nullable=True)     # 100文字要約（prompt注入用）
    data        = Column(JSON, nullable=False)    # 構造化データ
    # 出典管理
    source      = Column(String, nullable=False)  # 国土交通省/日銀/総務省 等
    source_url  = Column(Text, nullable=True)
    # 有効期限（陳腐化リスク対策）
    valid_from  = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)
    is_active   = Column(Integer, default=1)      # 0=expired, 1=active
    # タイムスタンプ
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InternalLink(Base):
    """
    内部リンクマップ
    - SEO Agentが記事間・記事→ツールのリンクを管理
    - 重複登録防止にUNIQUE制約
    """
    __tablename__ = "internal_links"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    from_slug   = Column(String, nullable=False)
    to_slug     = Column(String, nullable=False)   # ツールURLもここに格納
    anchor_text = Column(Text, nullable=True)
    link_type   = Column(String, nullable=True)    # tool / related / ranking / area
    created_at  = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("from_slug", "to_slug", name="uq_internal_link"),)


class SeoMetric(Base):
    """
    SEOパフォーマンス指標
    - Google Search Console連携用（Phase 2）
    - Analytics主導のトピック優先度調整に使用
    """
    __tablename__ = "seo_metrics"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    article_slug = Column(String, nullable=False)
    impressions  = Column(Integer, default=0)
    clicks       = Column(Integer, default=0)
    ctr          = Column(Float, default=0.0)
    avg_position = Column(Float, nullable=True)
    measured_at  = Column(Date, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("article_slug", "measured_at", name="uq_seo_metric"),)
