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
@Table(name = "competition")
public class Competition {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@Column(nullable = false, length = 50)
	private String source;

	@Column(name = "external_id", nullable = false, length = 100)
	private String externalId;

	@Column(nullable = false, length = 150)
	private String name;

	@Column(nullable = false, length = 20)
	private String season;

	@Column(nullable = false, length = 80)
	private String slug;
}
