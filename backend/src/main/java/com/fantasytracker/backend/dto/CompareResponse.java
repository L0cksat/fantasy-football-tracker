package com.fantasytracker.backend.dto;

import java.math.BigDecimal;
import java.util.List;

public record CompareResponse(
		Integer fromGameweek,
		Integer toGameweek,
		BigDecimal teamFromPoints,
		BigDecimal teamToPoints,
		BigDecimal teamDelta,
		List<PlayerDelta> players) {

	public record PlayerDelta(
			Long playerId,
			String name,
			String playerPortraitUrl,
			String position,
			String club,
			String fromRole,
			String toRole,
			BigDecimal fromPoints,
			BigDecimal toPoints,
			BigDecimal delta) {
	}
}
