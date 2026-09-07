package com.fantasytracker.backend.dto;

import java.math.BigDecimal;
import java.util.List;

import com.fantasytracker.backend.dto.SnapshotRequest.CompetitionPayload;
import com.fantasytracker.backend.dto.SnapshotRequest.PlayerPayload;
import com.fantasytracker.backend.dto.SnapshotRequest.TeamPayload;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;

public record TransfersRequest(
		@NotNull @Valid CompetitionPayload competition,
		@NotNull @Valid TeamPayload team,
		@NotEmpty @Valid List<RoundTransfers> rounds) {

	public record RoundTransfers(
			@NotNull Integer number,
			String name,
			BigDecimal transferPenalty,
			@NotNull @Valid List<TransferPair> transfers) {
	}

	public record TransferPair(
			@NotNull @Valid PlayerPayload playerIn,
			@NotNull @Valid PlayerPayload playerOut,
			BigDecimal priceIn,
			BigDecimal priceOut) {
	}
}
