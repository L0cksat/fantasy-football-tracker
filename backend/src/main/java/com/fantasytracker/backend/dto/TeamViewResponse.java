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
		List<TransferView> transfers,
		TransferMarketSummary transferMarket) {

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
			Integer shirtNumber,
			String role,
			boolean captain,
			boolean viceCaptain,
			int captainMultiplier,
			BigDecimal basePoints,
			BigDecimal points,
			BigDecimal rating,
			String breakdown,
			boolean injured,
			boolean suspended) {
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
			BigDecimal price,
			String counterpart,
			String channel) {
	}

	public record TransferMarketSummary(
			TransferMarketScope week,
			TransferMarketScope season,
			TransferHighlight mostExpensivePurchase,
			TransferHighlight highestSale) {
	}

	public record TransferHighlight(
			Long playerId,
			String externalId,
			String name,
			String playerPortraitUrl,
			String position,
			String club,
			String clubCrestUrl,
			Integer shirtNumber,
			BigDecimal price,
			String counterpart,
			String channel,
			Integer gameweekNumber,
			String gameweekName) {
	}

	public record TransferMarketScope(
			DealGroup soldToMarket,
			DealGroup soldReleaseClause,
			DealGroup boughtFromMarket,
			DealGroup boughtReleaseClause,
			List<CounterpartGroup> soldTo,
			List<CounterpartGroup> boughtFrom) {
	}

	public record DealGroup(int count, BigDecimal total) {
	}

	public record CounterpartGroup(String name, int count, BigDecimal total) {
	}
}
