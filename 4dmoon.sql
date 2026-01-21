-- =========================
-- Database: 4dmoon
-- =========================

CREATE DATABASE IF NOT EXISTS `4dmoon`;
USE `4dmoon`;

-- =========================
-- Table: draw
-- =========================
CREATE TABLE IF NOT EXISTS draw (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  draw_date DATE NOT NULL,
  provider VARCHAR(50) NOT NULL,          -- Damacai, Magnum, SportsToto, Sabah, Singapore
  game VARCHAR(50) NOT NULL,              -- 1+3D, 4D, 3+3D, Lotto, 5D, 6D, Life
  title VARCHAR(100) NOT NULL,            -- title asal (full)
  draw_info VARCHAR(100) NULL,            -- "(Sat) 17-Jan-2026 #6023/26"
  first_prize VARCHAR(10) NULL,
  second_prize VARCHAR(10) NULL,
  third_prize VARCHAR(10) NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  UNIQUE KEY uq_draw (draw_date, title, draw_info)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================
-- Table: prize_number
-- =========================
CREATE TABLE IF NOT EXISTS prize_number (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  draw_id BIGINT UNSIGNED NOT NULL,
  kind ENUM('special','consolation') NOT NULL,
  pos TINYINT UNSIGNED NOT NULL,           -- 1..10
  number VARCHAR(10) NOT NULL,             -- kekalkan leading zero (contoh: 0026)

  CONSTRAINT fk_prize_draw
    FOREIGN KEY (draw_id) REFERENCES draw(id)
    ON DELETE CASCADE,

  UNIQUE KEY uq_prize (draw_id, kind, pos)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================
-- Table: raw_line (optional)
-- =========================
CREATE TABLE IF NOT EXISTS raw_line (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  draw_id BIGINT UNSIGNED NOT NULL,
  line_no SMALLINT UNSIGNED NOT NULL,
  line_text VARCHAR(255) NOT NULL,

  CONSTRAINT fk_raw_draw
    FOREIGN KEY (draw_id) REFERENCES draw(id)
    ON DELETE CASCADE,

  UNIQUE KEY uq_raw (draw_id, line_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
