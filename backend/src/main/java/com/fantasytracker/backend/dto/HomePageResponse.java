package com.fantasytracker.backend.dto;

import java.math.BigDecimal;
import java.util.List;

public record HomePageResponse(
		Long defaultCompetitionId,
		String defaultCompetitionSlug,
		List<LeagueBrand> leagueBrands,
		List<PlayerOfTheWeek> playersOfTheWeek) {

	public record LeagueBrand(
			String brandKey,
			String name,
			String logoUrl,
			String logoDarkUrl,
			String primaryColor,
			String secondaryColor) {
	}

	public record PlayerOfTheWeek(
			Long competitionId,
			String competitionName,
			String competitionSlug,
			String logoUrl,
			String primaryColor,
			String secondaryColor,
			int gameweek,
			String gameweekName,
			Long playerId,
			String externalId,
			String name,
			Integer shirtNumber,
			String position,
			String club,
			String playerPortraitUrl,
			String clubCrestUrl,
			BigDecimal points) {
	}
}
