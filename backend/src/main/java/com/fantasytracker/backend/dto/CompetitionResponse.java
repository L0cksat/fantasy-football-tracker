package com.fantasytracker.backend.dto;

import java.util.List;

public record CompetitionResponse(
		Long id,
		String source,
		String externalId,
		String name,
		String season,
		String slug,
		String teamName,
		List<Integer> gameweeks) {
}
