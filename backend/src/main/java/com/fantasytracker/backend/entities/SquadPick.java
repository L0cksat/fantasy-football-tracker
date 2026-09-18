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
@Table(name = "squad_pick")
public class SquadPick {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "fantasy_team_id", nullable = false)
	private FantasyTeam fantasyTeam;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "player_id", nullable = false)
	private Player player;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "gameweek_id", nullable = false)
	private Gameweek gameweek;

	@Column(nullable = false, length = 20)
	private String role;

	@Column(name = "is_captain", nullable = false)
	private boolean captain;

	@Column(name = "is_vice_captain", nullable = false)
	private boolean viceCaptain;

	@Column(precision = 12, scale = 6)
	private BigDecimal price;

	@Column(nullable = false)
	private boolean injured;

	@Column(nullable = false)
	private boolean suspended;

	/** Competition-context club / national side (not shared across competitions). */
	@Column(length = 150)
	private String club;

	@Column(name = "club_external_id", length = 50)
	private String clubExternalId;

	@Column(name = "shirt_number")
	private Integer shirtNumber;
}
