package com.fantasytracker.backend.entities;

import java.math.BigDecimal;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.Data;

@Data
@Entity
@Table(name = "player_gameweek_score")
public class PlayerGameweekScore {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "player_id", nullable = false)
	private Player player;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "gameweek_id", nullable = false)
	private Gameweek gameweek;

	@Column(nullable = false, precision = 6, scale = 1)
	private BigDecimal points;

	@Column(precision = 3, scale = 1)
	private BigDecimal rating;

	@Column(columnDefinition = "TEXT")
	private String breakdown;
}
