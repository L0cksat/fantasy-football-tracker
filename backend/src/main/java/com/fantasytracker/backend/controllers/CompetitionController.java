package com.fantasytracker.backend.controllers;

import java.util.List;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.fantasytracker.backend.dto.CompareResponse;
import com.fantasytracker.backend.dto.CompetitionResponse;
import com.fantasytracker.backend.dto.TeamViewResponse;
import com.fantasytracker.backend.dto.TotalsResponse;
import com.fantasytracker.backend.services.CompetitionQueryService;

@RestController
@RequestMapping("/api/v1/competitions")
public class CompetitionController {

	private final CompetitionQueryService queryService;

	public CompetitionController(CompetitionQueryService queryService) {
		this.queryService = queryService;
	}

	@GetMapping
	public ResponseEntity<List<CompetitionResponse>> list() {
		return ResponseEntity.ok(queryService.listCompetitions());
	}

	@GetMapping("/{id}/team")
	public ResponseEntity<TeamViewResponse> team(
			@PathVariable Long id,
			@RequestParam(required = false) Integer gameweek) {
		return ResponseEntity.ok(queryService.teamView(id, gameweek));
	}

	@GetMapping("/{id}/gameweeks/{n}")
	public ResponseEntity<TeamViewResponse> gameweek(@PathVariable Long id, @PathVariable("n") Integer n) {
		return ResponseEntity.ok(queryService.gameweekView(id, n));
	}

	@GetMapping("/{id}/compare")
	public ResponseEntity<CompareResponse> compare(
			@PathVariable Long id,
			@RequestParam("from") Integer from,
			@RequestParam("to") Integer to) {
		return ResponseEntity.ok(queryService.compare(id, from, to));
	}

	@GetMapping("/{id}/totals")
	public ResponseEntity<TotalsResponse> totals(@PathVariable Long id) {
		return ResponseEntity.ok(queryService.totals(id));
	}
}
