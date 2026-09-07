package com.fantasytracker.backend.controllers;

import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import com.fantasytracker.backend.dto.SnapshotRequest;
import com.fantasytracker.backend.dto.TransfersRequest;
import com.fantasytracker.backend.services.IngestService;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/v1/ingest")
public class IngestController {

	private final IngestService ingestService;
	private final String ingestToken;

	public IngestController(IngestService ingestService, @Value("${fantasy.ingest.token:}") String ingestToken) {
		this.ingestService = ingestService;
		this.ingestToken = ingestToken;
	}

	@PostMapping("/snapshots")
	public ResponseEntity<Map<String, Object>> ingest(
			@Valid @RequestBody SnapshotRequest request,
			@RequestHeader(value = "X-Ingest-Token", required = false) String token) {
		if (StringUtils.hasText(ingestToken) && !ingestToken.equals(token)) {
			throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid ingest token");
		}
		Long competitionId = ingestService.upsertSnapshot(request);
		return ResponseEntity.status(HttpStatus.CREATED).body(Map.of(
				"competitionId", competitionId,
				"gameweek", request.gameweek().number()));
	}

	@PostMapping("/transfers")
	public ResponseEntity<Map<String, Object>> ingestTransfers(
			@Valid @RequestBody TransfersRequest request,
			@RequestHeader(value = "X-Ingest-Token", required = false) String token) {
		if (StringUtils.hasText(ingestToken) && !ingestToken.equals(token)) {
			throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid ingest token");
		}
		Long competitionId = ingestService.upsertTransfers(request);
		return ResponseEntity.status(HttpStatus.CREATED).body(Map.of(
				"competitionId", competitionId,
				"rounds", request.rounds().size()));
	}

	@PostMapping("/cleanup-seed")
	public ResponseEntity<Map<String, Object>> cleanupSeed(
			@RequestHeader(value = "X-Ingest-Token", required = false) String token) {
		if (StringUtils.hasText(ingestToken) && !ingestToken.equals(token)) {
			throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid ingest token");
		}
		int removed = ingestService.removeSeedPlayers();
		return ResponseEntity.ok(Map.of("removedSeedPlayers", removed));
	}
}
