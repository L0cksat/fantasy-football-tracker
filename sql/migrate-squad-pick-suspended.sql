-- Suspended flag from SofaScore GW missingPlayers (yellow accumulation / red / unavailable).
ALTER TABLE squad_pick
  ADD COLUMN suspended TINYINT(1) NOT NULL DEFAULT 0 AFTER injured;
