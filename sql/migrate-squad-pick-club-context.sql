-- Club/national team context belongs on the squad pick, not the shared player row.
-- Same SofaScore player can be FC Barcelona in LaLiga and Spain in Nations League.
ALTER TABLE squad_pick
  ADD COLUMN club VARCHAR(150) NULL AFTER injured,
  ADD COLUMN club_external_id VARCHAR(50) NULL AFTER club,
  ADD COLUMN shirt_number INT NULL AFTER club_external_id;
