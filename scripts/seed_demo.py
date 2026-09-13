from app.db.session import Base, SessionLocal, engine
from app.models.entities import Property

Base.metadata.create_all(bind=engine)
db = SessionLocal()

rows = [
    Property(source_parcel_id="TX-DEMO-001", address="100 Main St", city="Anna",
             state="TX", county="Collin", zip_code="75409", acreage=0.25,
             estimated_value=225000, annual_taxes=4200, property_type="residential",
             distress_type="tax_sale", data_quality=92, latitude=33.349, longitude=-96.548),
    Property(source_parcel_id="TX-DEMO-002", address="200 County Road 12", city="Melissa",
             state="TX", county="Collin", zip_code="75454", acreage=12.4,
             estimated_value=610000, annual_taxes=9800, property_type="land",
             distress_type="government_land", data_quality=88, latitude=33.284, longitude=-96.572),
    Property(source_parcel_id="TX-DEMO-003", address="300 Oak Ave", city="Dallas",
             state="TX", county="Dallas", zip_code="75201", acreage=0.18,
             estimated_value=390000, annual_taxes=7200, property_type="residential",
             distress_type="mortgage_foreclosure", data_quality=95, latitude=32.78, longitude=-96.80),
]
for row in rows:
    db.add(row)
db.commit()
print(f"Seeded {len(rows)} demo properties.")
