package com.fantasytracker.backend.dto;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

public record TeamViewResponse(
		CompetitionSummary competition,
		TeamSummary team,
		GameweekSummary gameweek,
		BigDecimal teamPoints,
		boolean tripleCaptain,
		BigDecimal transferPenalty,
		List<PickView> picks,
		List<TransferView> transfers) {

	public record CompetitionSummary(
			Long id,
			String name,
			String season,
			String slug,
			String logoUrl,
			String logoDarkUrl,
			String flagUrl,
			String countryName,
			String primaryColor,
			String secondaryColor) {
	}

	public record TeamSummary(Long id, String name, String managerName) {
	}

	public record GameweekSummary(Integer number, String name, String status, LocalDate startsAt, LocalDate endsAt) {
	}

	public record PickView(
			Long playerId,
			String externalId,
			String name,
			String playerPortraitUrl,
			String position,
			String club,
			String clubCrestUrl,
			String role,
			boolean captain,
			boolean viceCaptain,
			int captainMultiplier,
			BigDecimal basePoints,
			BigDecimal points,
			BigDecimal rating,
			String breakdown) {
	}

	public record TransferView(
			String direction,
			Long playerId,
			String externalId,
			String name,
			String playerPortraitUrl,
			String position,
			String club,
			String clubCrestUrl,
			BigDecimal price) {
	}
}
