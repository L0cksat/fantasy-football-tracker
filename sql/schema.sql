-- Fantasy Football Tracker — MySQL 8 / MariaDB
-- Gameweeks are rows, not tables. Comparison and totals are queries.

CREATE DATABASE IF NOT EXISTS fantasy_tracker
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE fantasy_tracker;

CREATE TABLE IF NOT EXISTS competition (
  id BIGINT NOT NULL AUTO_INCREMENT,
  source VARCHAR(50) NOT NULL,
  external_id VARCHAR(100) NOT NULL,
  name VARCHAR(150) NOT NULL,
  season VARCHAR(20) NOT NULL,
  slug VARCHAR(80) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_competition_source (source, external_id, season)
);

CREATE TABLE IF NOT EXISTS gameweek (
  id BIGINT NOT NULL AUTO_INCREMENT,
  competition_id BIGINT NOT NULL,
  number INT NOT NULL,
  name VARCHAR(50) NULL,
  status VARCHAR(20) NOT NULL,
  starts_at DATE NULL,
  ends_at DATE NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_gameweek_comp_number (competition_id, number),
  CONSTRAINT fk_gameweek_competition
    FOREIGN KEY (competition_id) REFERENCES competition (id)
);

CREATE TABLE IF NOT EXISTS player (
  id BIGINT NOT NULL AUTO_INCREMENT,
  source VARCHAR(50) NOT NULL,
  external_id VARCHAR(100) NOT NULL,
  name VARCHAR(150) NOT NULL,
  position VARCHAR(10) NULL,
  club VARCHAR(150) NULL,
  club_external_id VARCHAR(50) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_player_source (source, external_id)
);

CREATE TABLE IF NOT EXISTS fantasy_team (
  id BIGINT NOT NULL AUTO_INCREMENT,
  competition_id BIGINT NOT NULL,
  name VARCHAR(150) NOT NULL,
  manager_name VARCHAR(150) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_team_competition (competition_id),
  CONSTRAINT fk_team_competition
    FOREIGN KEY (competition_id) REFERENCES competition (id)
);

CREATE TABLE IF NOT EXISTS squad_pick (
  id BIGINT NOT NULL AUTO_INCREMENT,
  fantasy_team_id BIGINT NOT NULL,
  player_id BIGINT NOT NULL,
  gameweek_id BIGINT NOT NULL,
  role VARCHAR(20) NOT NULL,
  is_captain TINYINT(1) NOT NULL DEFAULT 0,
  is_vice_captain TINYINT(1) NOT NULL DEFAULT 0,
  price DECIMAL(6,1) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_pick (fantasy_team_id, player_id, gameweek_id),
  CONSTRAINT fk_pick_team FOREIGN KEY (fantasy_team_id) REFERENCES fantasy_team (id),
  CONSTRAINT fk_pick_player FOREIGN KEY (player_id) REFERENCES player (id),
  CONSTRAINT fk_pick_gameweek FOREIGN KEY (gameweek_id) REFERENCES gameweek (id)
);

CREATE TABLE IF NOT EXISTS player_gameweek_score (
  id BIGINT NOT NULL AUTO_INCREMENT,
  player_id BIGINT NOT NULL,
  gameweek_id BIGINT NOT NULL,
  points DECIMAL(6,1) NOT NULL,
  rating DECIMAL(3,1) NULL,
  breakdown TEXT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_player_gw (player_id, gameweek_id),
  CONSTRAINT fk_pgs_player FOREIGN KEY (player_id) REFERENCES player (id),
  CONSTRAINT fk_pgs_gameweek FOREIGN KEY (gameweek_id) REFERENCES gameweek (id)
);

CREATE TABLE IF NOT EXISTS team_gameweek_score (
  id BIGINT NOT NULL AUTO_INCREMENT,
  fantasy_team_id BIGINT NOT NULL,
  gameweek_id BIGINT NOT NULL,
  points DECIMAL(6,1) NOT NULL,
  triple_captain TINYINT(1) NOT NULL DEFAULT 0,
  transfer_penalty DECIMAL(6,1) NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uk_team_gw (fantasy_team_id, gameweek_id),
  CONSTRAINT fk_tgs_team FOREIGN KEY (fantasy_team_id) REFERENCES fantasy_team (id),
  CONSTRAINT fk_tgs_gameweek FOREIGN KEY (gameweek_id) REFERENCES gameweek (id)
);

CREATE TABLE IF NOT EXISTS gameweek_transfer (
  id BIGINT NOT NULL AUTO_INCREMENT,
  fantasy_team_id BIGINT NOT NULL,
  gameweek_id BIGINT NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  player_in_id BIGINT NOT NULL,
  player_out_id BIGINT NOT NULL,
  price_in DECIMAL(6,1) NULL,
  price_out DECIMAL(6,1) NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_gt_team FOREIGN KEY (fantasy_team_id) REFERENCES fantasy_team (id),
  CONSTRAINT fk_gt_gameweek FOREIGN KEY (gameweek_id) REFERENCES gameweek (id),
  CONSTRAINT fk_gt_player_in FOREIGN KEY (player_in_id) REFERENCES player (id),
  CONSTRAINT fk_gt_player_out FOREIGN KEY (player_out_id) REFERENCES player (id)
);
