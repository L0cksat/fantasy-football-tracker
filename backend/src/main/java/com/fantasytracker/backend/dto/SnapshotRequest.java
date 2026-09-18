package com.fantasytracker.backend.dto;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;

public record SnapshotRequest(
		@NotNull @Valid CompetitionPayload competition,
		@NotNull @Valid GameweekPayload gameweek,
		@NotNull @Valid TeamPayload team,
		@NotEmpty @Valid List<PickPayload> picks,
		BigDecimal teamPoints,
		boolean tripleCaptain,
		BigDecimal transferPenalty) {

	public record CompetitionPayload(
			@NotBlank String source,
			@NotBlank String externalId,
			@NotBlank String name,
			@NotBlank String season,
			@NotBlank String slug) {
	}

	public record GameweekPayload(
			@NotNull Integer number,
			String name,
			@NotBlank String status,
			LocalDate startsAt,
			LocalDate endsAt) {
	}

	public record TeamPayload(
			@NotBlank String name,
			String managerName) {
	}

	public record PlayerPayload(
			@NotBlank String externalId,
			@NotBlank String name,
			String position,
			String club,
			String clubExternalId,
			Integer shirtNumber) {
	}

	public record PickPayload(
			@NotNull @Valid PlayerPayload player,
			@NotBlank String role,
			boolean captain,
			boolean viceCaptain,
			@NotNull BigDecimal points,
			BigDecimal rating,
			BigDecimal price,
			Map<String, Object> breakdown,
			boolean injured,
			boolean suspended) {
	}
}
