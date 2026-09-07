package com.fantasytracker.backend.entities;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Data;

@Data
@Entity
@Table(name = "player")
public class Player {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@Column(nullable = false, length = 50)
	private String source;

	@Column(name = "external_id", nullable = false, length = 100)
	private String externalId;

	@Column(nullable = false, length = 150)
	private String name;

	@Column(length = 10)
	private String position;

	@Column(length = 150)
	private String club;

	@Column(name = "club_external_id", length = 50)
	private String clubExternalId;
}
