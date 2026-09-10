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
@Table(name = "gameweek_transfer")
public class GameweekTransfer {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "fantasy_team_id", nullable = false)
	private FantasyTeam fantasyTeam;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "gameweek_id", nullable = false)
	private Gameweek gameweek;

	@Column(name = "sort_order", nullable = false)
	private int sortOrder;

	@ManyToOne(fetch = FetchType.LAZY)
	@JoinColumn(name = "player_in_id")
	private Player playerIn;

	@ManyToOne(fetch = FetchType.LAZY)
	@JoinColumn(name = "player_out_id")
	private Player playerOut;

	@Column(name = "price_in", precision = 12, scale = 6)
	private BigDecimal priceIn;

	@Column(name = "price_out", precision = 12, scale = 6)
	private BigDecimal priceOut;

	@Column(name = "counterpart", length = 120)
	private String counterpart;
}
