from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class GridCell(Base):
    __tablename__ = "grid_cells"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cell_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    city: Mapped[str] = mapped_column(String(64), index=True)
    centroid_lat: Mapped[float] = mapped_column(Float)
    centroid_lon: Mapped[float] = mapped_column(Float)
    geometry_json: Mapped[str] = mapped_column(Text)
    temperature_c: Mapped[float] = mapped_column(Float)
    tree_cover_pct: Mapped[float] = mapped_column(Float)
    impervious_pct: Mapped[float] = mapped_column(Float)
    traffic_index: Mapped[float] = mapped_column(Float)
    water_proximity_m: Mapped[float] = mapped_column(Float)
    population_proxy: Mapped[float] = mapped_column(Float, default=0.5)
    vulnerability: Mapped[float] = mapped_column(Float, default=0.5)
