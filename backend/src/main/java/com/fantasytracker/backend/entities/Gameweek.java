package com.fantasytracker.backend.entities;

import java.time.LocalDate;

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
@Table(name = "gameweek")
public class Gameweek {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "competition_id", nullable = false)
	private Competition competition;

	@Column(nullable = false)
	private Integer number;

	@Column(length = 50)
	private String name;

	@Column(nullable = false, length = 20)
	private String status;

	@Column(name = "starts_at")
	private LocalDate startsAt;

	@Column(name = "ends_at")
	private LocalDate endsAt;
}
