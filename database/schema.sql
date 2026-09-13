CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS properties (
  id uuid PRIMARY KEY,
  source_parcel_id text,
  address text,
  city text,
  state char(2) NOT NULL,
  county text,
  zip_code text,
  acreage double precision,
  estimated_value double precision,
  annual_taxes double precision,
  property_type text,
  distress_type text,
  data_quality double precision NOT NULL DEFAULT 0,
  latitude double precision,
  longitude double precision,
  geometry geometry(MultiPolygon, 4326),
  raw_data jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_properties_geometry
ON properties USING GIST (geometry);

CREATE INDEX IF NOT EXISTS ix_properties_location
ON properties (state, county, city);
