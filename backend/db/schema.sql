-- Core tables
CREATE TABLE persons (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name_fr TEXT NOT NULL,
  name_ar TEXT,
  name_variants TEXT[],
  birth_year INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE institutions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name_fr TEXT NOT NULL,
  name_ar TEXT,
  name_variants TEXT[],
  type TEXT CHECK (type IN ('ministry','agency','court','commission','soe','other')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE decrees (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  decree_number TEXT,
  jort_issue TEXT,
  date_published DATE,
  date_effective DATE,
  decree_type TEXT,
  raw_text TEXT,
  source_file TEXT,
  confidence FLOAT,
  needs_review BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Temporal relations (the core of the data model)
CREATE TABLE person_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID REFERENCES persons(id),
  institution_id UUID REFERENCES institutions(id),
  role_fr TEXT NOT NULL,
  role_ar TEXT,
  valid_from DATE,
  valid_to DATE,         -- NULL = still active
  decree_id UUID REFERENCES decrees(id),
  action TEXT
);

CREATE TABLE institution_hierarchy (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  child_id UUID REFERENCES institutions(id),
  parent_id UUID REFERENCES institutions(id),
  valid_from DATE,
  valid_to DATE,
  decree_id UUID REFERENCES decrees(id)
);

CREATE TABLE institution_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id UUID REFERENCES institutions(id),
  event_type TEXT,       -- created, dissolved, renamed, merged_into
  event_date DATE,
  target_institution_id UUID REFERENCES institutions(id),
  decree_id UUID REFERENCES decrees(id)
);

-- Semantic search (Requires pgvector)
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE decrees ADD COLUMN embedding vector(1536);
-- Note: ivfflat index creation might fail if table is empty or too small, 
-- but we define it for the schema.
-- CREATE INDEX ON decrees USING ivfflat (embedding vector_cosine_ops);

-- Full-text search
ALTER TABLE decrees ADD COLUMN search_vector tsvector;
CREATE INDEX ON decrees USING GIN (search_vector);

-- Apache AGE Extension (Graph support)
-- This setup requires AGE installed on the postgres instance.
-- CREATE EXTENSION IF NOT EXISTS age;
-- LOAD 'age';
-- SET search_path = ag_catalog, "$user", public;
-- SELECT create_graph('marsad_graph');
