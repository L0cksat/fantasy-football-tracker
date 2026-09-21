package com.fantasytracker.backend.dto;

import java.math.BigDecimal;
import java.util.List;

public record TotalsResponse(
		Long competitionId,
		String teamName,
		BigDecimal totalPoints,
		List<GameweekTotal> gameweeks) {

	public record GameweekTotal(Integer number, String name, String status, BigDecimal points) {
	}
}
