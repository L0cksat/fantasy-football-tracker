package com.fantasytracker.backend.services;

import java.math.BigDecimal;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.fantasytracker.backend.dto.SnapshotRequest;
import com.fantasytracker.backend.dto.SnapshotRequest.CompetitionPayload;
import com.fantasytracker.backend.dto.SnapshotRequest.PickPayload;
import com.fantasytracker.backend.dto.SnapshotRequest.PlayerPayload;
import com.fantasytracker.backend.dto.SnapshotRequest.TeamPayload;
import com.fantasytracker.backend.dto.TransfersRequest;
import com.fantasytracker.backend.dto.TransfersRequest.RoundTransfers;
import com.fantasytracker.backend.dto.TransfersRequest.TransferPair;
import com.fantasytracker.backend.entities.Competition;
import com.fantasytracker.backend.entities.FantasyTeam;
import com.fantasytracker.backend.entities.Gameweek;
import com.fantasytracker.backend.entities.GameweekTransfer;
import com.fantasytracker.backend.entities.Player;
import com.fantasytracker.backend.entities.PlayerGameweekScore;
import com.fantasytracker.backend.entities.SquadPick;
import com.fantasytracker.backend.entities.TeamGameweekScore;
import com.fantasytracker.backend.repositories.CompetitionRepository;
import com.fantasytracker.backend.repositories.FantasyTeamRepository;
import com.fantasytracker.backend.repositories.GameweekRepository;
import com.fantasytracker.backend.repositories.GameweekTransferRepository;
import com.fantasytracker.backend.repositories.PlayerGameweekScoreRepository;
import com.fantasytracker.backend.repositories.PlayerRepository;
import com.fantasytracker.backend.repositories.SquadPickRepository;
import com.fantasytracker.backend.repositories.TeamGameweekScoreRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

@Service
public class IngestService {

	private final CompetitionRepository competitionRepository;
	private final GameweekRepository gameweekRepository;
	private final PlayerRepository playerRepository;
	private final FantasyTeamRepository fantasyTeamRepository;
	private final SquadPickRepository squadPickRepository;
	private final PlayerGameweekScoreRepository playerScoreRepository;
	private final TeamGameweekScoreRepository teamScoreRepository;
	private final GameweekTransferRepository transferRepository;
	private final ObjectMapper objectMapper;

	public IngestService(
			CompetitionRepository competitionRepository,
			GameweekRepository gameweekRepository,
			PlayerRepository playerRepository,
			FantasyTeamRepository fantasyTeamRepository,
			SquadPickRepository squadPickRepository,
			PlayerGameweekScoreRepository playerScoreRepository,
			TeamGameweekScoreRepository teamScoreRepository,
			GameweekTransferRepository transferRepository,
			ObjectMapper objectMapper) {
		this.competitionRepository = competitionRepository;
		this.gameweekRepository = gameweekRepository;
		this.playerRepository = playerRepository;
		this.fantasyTeamRepository = fantasyTeamRepository;
		this.squadPickRepository = squadPickRepository;
		this.playerScoreRepository = playerScoreRepository;
		this.teamScoreRepository = teamScoreRepository;
		this.transferRepository = transferRepository;
		this.objectMapper = objectMapper;
	}

	@Transactional
	public Long upsertSnapshot(SnapshotRequest request) {
		Competition competition = upsertCompetition(request);
		Gameweek gameweek = upsertGameweek(competition, request);
		FantasyTeam team = upsertTeam(competition, request);
		BigDecimal starterPoints = BigDecimal.ZERO;
		Set<Long> keepPlayerIds = new HashSet<>();

		for (PickPayload pick : request.picks()) {
			Player player = upsertPlayer(competition.getSource(), pick);
			keepPlayerIds.add(player.getId());
			upsertPick(team, player, gameweek, pick);
			upsertPlayerScore(player, gameweek, pick);
			if ("starter".equalsIgnoreCase(pick.role())) {
				starterPoints = starterPoints.add(
						CaptainScoring.effective(pick.points(), pick.captain(), request.tripleCaptain()));
			}
		}

		removeStalePicks(team, gameweek, keepPlayerIds);
		BigDecimal teamPoints = request.teamPoints() != null ? request.teamPoints() : starterPoints;
		upsertTeamScore(team, gameweek, teamPoints, request.tripleCaptain(), request.transferPenalty());
		return competition.getId();
	}

	@Transactional
	public Long upsertTransfers(TransfersRequest request) {
		Competition competition = upsertCompetition(request.competition());
		FantasyTeam team = upsertTeam(competition, request.team());
		for (RoundTransfers round : request.rounds()) {
			Gameweek gameweek = upsertGameweekForTransfers(competition, round);
			transferRepository.deleteByFantasyTeam_IdAndGameweek_Id(team.getId(), gameweek.getId());
			int order = 0;
			for (TransferPair pair : round.transfers()) {
				if (pair.playerIn() == null && pair.playerOut() == null) {
					throw new IllegalArgumentException("Each transfer needs a bought or sold player");
				}
				GameweekTransfer row = new GameweekTransfer();
				row.setFantasyTeam(team);
				row.setGameweek(gameweek);
				row.setSortOrder(order++);
				if (pair.playerIn() != null) {
					row.setPlayerIn(upsertPlayer(competition.getSource(), pair.playerIn()));
				}
				if (pair.playerOut() != null) {
					row.setPlayerOut(upsertPlayer(competition.getSource(), pair.playerOut()));
				}
				row.setPriceIn(pair.priceIn());
				row.setPriceOut(pair.priceOut());
				row.setCounterpart(pair.counterpart());
				transferRepository.save(row);
			}
			applyTransferPenalty(team, gameweek, round.transferPenalty());
		}
		return competition.getId();
	}

	@Transactional
	public int removeSeedPlayers() {
		List<Player> seeds = playerRepository.findByExternalIdStartingWith("ss-");
		for (Player player : seeds) {
			squadPickRepository.deleteByPlayer_Id(player.getId());
			playerScoreRepository.deleteByPlayer_Id(player.getId());
			playerRepository.delete(player);
		}
		return seeds.size();
	}

	private void removeStalePicks(FantasyTeam team, Gameweek gameweek, Set<Long> keepPlayerIds) {
		List<SquadPick> existing = squadPickRepository.findByFantasyTeam_IdAndGameweek_Id(team.getId(), gameweek.getId());
		for (SquadPick pick : existing) {
			Long playerId = pick.getPlayer().getId();
			if (!keepPlayerIds.contains(playerId)) {
				squadPickRepository.delete(pick);
				playerScoreRepository.findByPlayer_IdAndGameweek_Id(playerId, gameweek.getId())
						.ifPresent(playerScoreRepository::delete);
			}
		}
	}

	private Competition upsertCompetition(SnapshotRequest request) {
		return upsertCompetition(request.competition());
	}

	private Competition upsertCompetition(CompetitionPayload payload) {
		Competition competition = competitionRepository
				.findBySourceAndExternalIdAndSeason(payload.source(), payload.externalId(), payload.season())
				.orElseGet(Competition::new);
		competition.setSource(payload.source());
		competition.setExternalId(payload.externalId());
		competition.setName(payload.name());
		competition.setSeason(payload.season());
		competition.setSlug(payload.slug());
		return competitionRepository.save(competition);
	}

	private Gameweek upsertGameweek(Competition competition, SnapshotRequest request) {
		var payload = request.gameweek();
		Gameweek gameweek = gameweekRepository
				.findByCompetition_IdAndNumber(competition.getId(), payload.number())
				.orElseGet(Gameweek::new);
		gameweek.setCompetition(competition);
		gameweek.setNumber(payload.number());
		gameweek.setName(payload.name() != null ? payload.name() : "GW" + payload.number());
		gameweek.setStatus(payload.status());
		gameweek.setStartsAt(payload.startsAt());
		gameweek.setEndsAt(payload.endsAt());
		return gameweekRepository.save(gameweek);
	}

	private FantasyTeam upsertTeam(Competition competition, SnapshotRequest request) {
		return upsertTeam(competition, request.team());
	}

	private FantasyTeam upsertTeam(Competition competition, TeamPayload payload) {
		FantasyTeam team = fantasyTeamRepository
				.findByCompetition_Id(competition.getId())
				.orElseGet(FantasyTeam::new);
		team.setCompetition(competition);
		team.setName(payload.name());
		team.setManagerName(payload.managerName());
		return fantasyTeamRepository.save(team);
	}

	private Gameweek upsertGameweekForTransfers(Competition competition, RoundTransfers round) {
		Gameweek gameweek = gameweekRepository
				.findByCompetition_IdAndNumber(competition.getId(), round.number())
				.orElseGet(Gameweek::new);
		boolean created = gameweek.getId() == null;
		gameweek.setCompetition(competition);
		gameweek.setNumber(round.number());
		if (round.name() != null && !round.name().isBlank()) {
			gameweek.setName(round.name());
		} else if (gameweek.getName() == null) {
			gameweek.setName("GW" + round.number());
		}
		if (created) {
			gameweek.setStatus("upcoming");
		}
		return gameweekRepository.save(gameweek);
	}

	private void applyTransferPenalty(FantasyTeam team, Gameweek gameweek, BigDecimal penalty) {
		BigDecimal value = penalty != null ? penalty : BigDecimal.ZERO;
		teamScoreRepository.findByFantasyTeam_IdAndGameweek_Id(team.getId(), gameweek.getId())
				.ifPresent(score -> {
					score.setTransferPenalty(value);
					teamScoreRepository.save(score);
				});
	}

	private Player upsertPlayer(String source, PickPayload pick) {
		return upsertPlayer(source, pick.player());
	}

	private Player upsertPlayer(String source, PlayerPayload payload) {
		Player player = playerRepository
				.findBySourceAndExternalId(source, payload.externalId())
				.orElseGet(Player::new);
		player.setSource(source);
		player.setExternalId(payload.externalId());
		player.setName(payload.name());
		player.setPosition(payload.position());
		player.setClub(payload.club());
		if (payload.clubExternalId() != null && !payload.clubExternalId().isBlank()) {
			player.setClubExternalId(payload.clubExternalId());
		}
		return playerRepository.save(player);
	}

	private void upsertPick(FantasyTeam team, Player player, Gameweek gameweek, PickPayload pick) {
		SquadPick squadPick = squadPickRepository
				.findByFantasyTeam_IdAndPlayer_IdAndGameweek_Id(team.getId(), player.getId(), gameweek.getId())
				.orElseGet(SquadPick::new);
		squadPick.setFantasyTeam(team);
		squadPick.setPlayer(player);
		squadPick.setGameweek(gameweek);
		squadPick.setRole(pick.role());
		squadPick.setCaptain(pick.captain());
		squadPick.setViceCaptain(pick.viceCaptain());
		squadPick.setPrice(pick.price());
		squadPickRepository.save(squadPick);
	}

	private void upsertPlayerScore(Player player, Gameweek gameweek, PickPayload pick) {
		PlayerGameweekScore score = playerScoreRepository
				.findByPlayer_IdAndGameweek_Id(player.getId(), gameweek.getId())
				.orElseGet(PlayerGameweekScore::new);
		score.setPlayer(player);
		score.setGameweek(gameweek);
		score.setPoints(pick.points());
		score.setRating(pick.rating());
		score.setBreakdown(toJson(pick.breakdown()));
		playerScoreRepository.save(score);
	}

	private void upsertTeamScore(
			FantasyTeam team,
			Gameweek gameweek,
			BigDecimal points,
			boolean tripleCaptain,
			BigDecimal transferPenalty) {
		TeamGameweekScore score = teamScoreRepository
				.findByFantasyTeam_IdAndGameweek_Id(team.getId(), gameweek.getId())
				.orElseGet(TeamGameweekScore::new);
		score.setFantasyTeam(team);
		score.setGameweek(gameweek);
		score.setPoints(points);
		score.setTripleCaptain(tripleCaptain);
		score.setTransferPenalty(transferPenalty != null ? transferPenalty : BigDecimal.ZERO);
		teamScoreRepository.save(score);
	}

	private String toJson(java.util.Map<String, Object> breakdown) {
		if (breakdown == null || breakdown.isEmpty()) {
			return null;
		}
		try {
			return objectMapper.writeValueAsString(breakdown);
		} catch (JsonProcessingException ex) {
			return null;
		}
	}

	@Transactional(readOnly = true)
	public List<Competition> findAllCompetitions() {
		return competitionRepository.findAll();
	}
}
