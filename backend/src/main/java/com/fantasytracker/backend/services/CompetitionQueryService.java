package com.fantasytracker.backend.services;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import com.fantasytracker.backend.dto.CompareResponse;
import com.fantasytracker.backend.dto.CompetitionResponse;
import com.fantasytracker.backend.dto.TeamViewResponse;
import com.fantasytracker.backend.dto.TotalsResponse;
import com.fantasytracker.backend.entities.Competition;
import com.fantasytracker.backend.entities.FantasyTeam;
import com.fantasytracker.backend.entities.Gameweek;
import com.fantasytracker.backend.entities.Player;
import com.fantasytracker.backend.entities.PlayerGameweekScore;
import com.fantasytracker.backend.entities.SquadPick;
import com.fantasytracker.backend.entities.TeamGameweekScore;
import com.fantasytracker.backend.repositories.CompetitionRepository;
import com.fantasytracker.backend.repositories.FantasyTeamRepository;
import com.fantasytracker.backend.repositories.GameweekRepository;
import com.fantasytracker.backend.repositories.PlayerGameweekScoreRepository;
import com.fantasytracker.backend.repositories.SquadPickRepository;
import com.fantasytracker.backend.entities.GameweekTransfer;
import com.fantasytracker.backend.repositories.GameweekTransferRepository;
import com.fantasytracker.backend.repositories.TeamGameweekScoreRepository;

@Service
@Transactional(readOnly = true)
public class CompetitionQueryService {

	private final CompetitionRepository competitionRepository;
	private final GameweekRepository gameweekRepository;
	private final FantasyTeamRepository fantasyTeamRepository;
	private final SquadPickRepository squadPickRepository;
	private final PlayerGameweekScoreRepository playerScoreRepository;
	private final TeamGameweekScoreRepository teamScoreRepository;
	private final GameweekTransferRepository transferRepository;

	public CompetitionQueryService(
			CompetitionRepository competitionRepository,
			GameweekRepository gameweekRepository,
			FantasyTeamRepository fantasyTeamRepository,
			SquadPickRepository squadPickRepository,
			PlayerGameweekScoreRepository playerScoreRepository,
			TeamGameweekScoreRepository teamScoreRepository,
			GameweekTransferRepository transferRepository) {
		this.competitionRepository = competitionRepository;
		this.gameweekRepository = gameweekRepository;
		this.fantasyTeamRepository = fantasyTeamRepository;
		this.squadPickRepository = squadPickRepository;
		this.playerScoreRepository = playerScoreRepository;
		this.teamScoreRepository = teamScoreRepository;
		this.transferRepository = transferRepository;
	}

	public List<CompetitionResponse> listCompetitions() {
		return competitionRepository.findAll().stream()
				.map(this::toCompetitionResponse)
				.toList();
	}

	public TeamViewResponse teamView(Long competitionId, Integer gameweekNumber) {
		Competition competition = requireCompetition(competitionId);
		FantasyTeam team = requireTeam(competitionId);
		List<Gameweek> gameweeks = gameweekRepository.findByCompetition_IdOrderByNumberAsc(competitionId);
		if (gameweeks.isEmpty()) {
			throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No gameweeks ingested yet");
		}
		Gameweek gameweek = resolveGameweek(gameweeks, gameweekNumber);
		return buildTeamView(competition, team, gameweek);
	}

	public TeamViewResponse gameweekView(Long competitionId, Integer gameweekNumber) {
		return teamView(competitionId, gameweekNumber);
	}

	public CompareResponse compare(Long competitionId, Integer from, Integer to) {
		if (from == null || to == null) {
			throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "from and to gameweeks are required");
		}
		Competition competition = requireCompetition(competitionId);
		FantasyTeam team = requireTeam(competitionId);
		Gameweek fromGw = requireGameweek(competitionId, from);
		Gameweek toGw = requireGameweek(competitionId, to);

		List<SquadPick> fromPicks = squadPickRepository.findByFantasyTeam_IdAndGameweek_Id(team.getId(), fromGw.getId());
		List<SquadPick> toPicks = squadPickRepository.findByFantasyTeam_IdAndGameweek_Id(team.getId(), toGw.getId());

		Map<Long, SquadPick> fromByPlayer = indexPicks(fromPicks);
		Map<Long, SquadPick> toByPlayer = indexPicks(toPicks);

		Set<Long> playerIds = new LinkedHashSet<>();
		fromByPlayer.keySet().forEach(playerIds::add);
		toByPlayer.keySet().forEach(playerIds::add);

		Map<Long, PlayerGameweekScore> fromScores = indexScores(
				playerScoreRepository.findByGameweek_IdAndPlayer_IdIn(fromGw.getId(), playerIds));
		Map<Long, PlayerGameweekScore> toScores = indexScores(
				playerScoreRepository.findByGameweek_IdAndPlayer_IdIn(toGw.getId(), playerIds));
		boolean fromTriple = tripleCaptain(team.getId(), fromGw.getId());
		boolean toTriple = tripleCaptain(team.getId(), toGw.getId());

		List<CompareResponse.PlayerDelta> deltas = new ArrayList<>();
		for (Long playerId : playerIds) {
			SquadPick fromPick = fromByPlayer.get(playerId);
			SquadPick toPick = toByPlayer.get(playerId);
			Player player = fromPick != null ? fromPick.getPlayer() : toPick.getPlayer();
			SquadPick clubPick = toPick != null ? toPick : fromPick;
			BigDecimal fromPoints = CaptainScoring.effective(
					pointsOf(fromScores.get(playerId)),
					fromPick != null && fromPick.isCaptain(),
					fromTriple);
			BigDecimal toPoints = CaptainScoring.effective(
					pointsOf(toScores.get(playerId)),
					toPick != null && toPick.isCaptain(),
					toTriple);
			deltas.add(new CompareResponse.PlayerDelta(
					player.getId(),
					player.getName(),
					PlayerPortraits.url(competition.getSource(), player.getExternalId()),
					player.getPosition(),
					clubOf(clubPick),
					fromPick != null ? fromPick.getRole() : null,
					toPick != null ? toPick.getRole() : null,
					fromPoints,
					toPoints,
					toPoints.subtract(fromPoints)));
		}
		deltas.sort(Comparator.comparing(CompareResponse.PlayerDelta::delta).reversed());

		BigDecimal teamFrom = teamScoreRepository
				.findByFantasyTeam_IdAndGameweek_Id(team.getId(), fromGw.getId())
				.map(TeamGameweekScore::getPoints)
				.orElse(BigDecimal.ZERO);
		BigDecimal teamTo = teamScoreRepository
				.findByFantasyTeam_IdAndGameweek_Id(team.getId(), toGw.getId())
				.map(TeamGameweekScore::getPoints)
				.orElse(BigDecimal.ZERO);

		return new CompareResponse(from, to, teamFrom, teamTo, teamTo.subtract(teamFrom), deltas);
	}

	public TotalsResponse totals(Long competitionId) {
		requireCompetition(competitionId);
		FantasyTeam team = requireTeam(competitionId);
		List<TeamGameweekScore> scores = teamScoreRepository.findByFantasyTeam_IdOrderByGameweek_NumberAsc(team.getId());
		List<TotalsResponse.GameweekTotal> weeks = scores.stream()
				.map(score -> new TotalsResponse.GameweekTotal(
						score.getGameweek().getNumber(),
						score.getGameweek().getName(),
						score.getGameweek().getStatus(),
						score.getPoints()))
				.toList();
		BigDecimal total = weeks.stream()
				.map(TotalsResponse.GameweekTotal::points)
				.reduce(BigDecimal.ZERO, BigDecimal::add);
		return new TotalsResponse(competitionId, team.getName(), total, weeks);
	}

	private CompetitionResponse toCompetitionResponse(Competition competition) {
		FantasyTeam team = fantasyTeamRepository.findByCompetition_Id(competition.getId()).orElse(null);
		List<Integer> numbers = gameweekRepository.findByCompetition_IdOrderByNumberAsc(competition.getId()).stream()
				.map(Gameweek::getNumber)
				.toList();
		return new CompetitionResponse(
				competition.getId(),
				competition.getSource(),
				competition.getExternalId(),
				competition.getName(),
				competition.getSeason(),
				competition.getSlug(),
				team != null ? team.getName() : null,
				numbers,
				CompetitionBranding.logoUrl(competition.getSource(), competition.getExternalId()),
				CompetitionBranding.logoDarkUrl(competition.getSource(), competition.getExternalId()),
				CompetitionBranding.flagUrl(competition.getSource(), competition.getExternalId()),
				CompetitionBranding.countryName(competition.getSource(), competition.getExternalId()),
				CompetitionBranding.primaryColor(competition.getSource(), competition.getExternalId()),
				CompetitionBranding.secondaryColor(competition.getSource(), competition.getExternalId()));
	}

	private TeamViewResponse buildTeamView(Competition competition, FantasyTeam team, Gameweek gameweek) {
		List<SquadPick> picks = squadPickRepository.findByFantasyTeam_IdAndGameweek_Id(team.getId(), gameweek.getId());
		List<Long> playerIds = picks.stream().map(pick -> pick.getPlayer().getId()).toList();
		Map<Long, PlayerGameweekScore> scores = indexScores(
				playerScoreRepository.findByGameweek_IdAndPlayer_IdIn(gameweek.getId(), playerIds));
		TeamGameweekScore teamScore = teamScoreRepository
				.findByFantasyTeam_IdAndGameweek_Id(team.getId(), gameweek.getId())
				.orElse(null);
		boolean tripleCaptain = teamScore != null && teamScore.isTripleCaptain();
		BigDecimal transferPenalty = teamScore != null && teamScore.getTransferPenalty() != null
				? teamScore.getTransferPenalty()
				: BigDecimal.ZERO;
		List<TeamViewResponse.PickView> pickViews = picks.stream()
				.sorted(pickComparator())
				.map(pick -> {
					Player player = pick.getPlayer();
					PlayerGameweekScore score = scores.get(player.getId());
					BigDecimal base = score != null ? score.getPoints() : BigDecimal.ZERO;
					int multiplier = CaptainScoring.multiplier(pick.isCaptain(), tripleCaptain);
					String club = clubOf(pick);
					String clubExternalId = clubExternalIdOf(pick);
					Integer shirtNumber = shirtNumberOf(pick);
					return new TeamViewResponse.PickView(
							player.getId(),
							player.getExternalId(),
							player.getName(),
							PlayerPortraits.url(competition.getSource(), player.getExternalId()),
							player.getPosition(),
							club,
							ClubCrests.url(competition.getSource(), clubExternalId, club),
							shirtNumber,
							pick.getRole(),
							pick.isCaptain(),
							pick.isViceCaptain(),
							multiplier,
							base,
							CaptainScoring.effective(base, pick.isCaptain(), tripleCaptain),
							score != null ? score.getRating() : null,
							score != null ? score.getBreakdown() : null,
							pick.isInjured(),
							pick.isSuspended());
				})
				.toList();
		BigDecimal teamPoints = teamScore != null ? teamScore.getPoints() : BigDecimal.ZERO;
		return new TeamViewResponse(
				new TeamViewResponse.CompetitionSummary(
						competition.getId(),
						competition.getName(),
						competition.getSeason(),
						competition.getSlug(),
						CompetitionBranding.logoUrl(competition.getSource(), competition.getExternalId()),
						CompetitionBranding.logoDarkUrl(competition.getSource(), competition.getExternalId()),
						CompetitionBranding.flagUrl(competition.getSource(), competition.getExternalId()),
						CompetitionBranding.countryName(competition.getSource(), competition.getExternalId()),
						CompetitionBranding.primaryColor(competition.getSource(), competition.getExternalId()),
						CompetitionBranding.secondaryColor(competition.getSource(), competition.getExternalId())),
				new TeamViewResponse.TeamSummary(team.getId(), team.getName(), team.getManagerName()),
				new TeamViewResponse.GameweekSummary(
						gameweek.getNumber(), gameweek.getName(), gameweek.getStatus(),
						gameweek.getStartsAt(), gameweek.getEndsAt()),
				teamPoints,
				tripleCaptain,
				transferPenalty,
				pickViews,
				buildTransfers(competition, team, gameweek),
				buildTransferMarket(competition, team, gameweek),
				findLongestServingPlayer(competition, team));
	}

	/**
	 * Official LaLiga only: most gameweeks as a starter; ties broken by total points scored
	 * for the team in those starter weeks.
	 */
	private TeamViewResponse.LongestServingPlayer findLongestServingPlayer(
			Competition competition,
			FantasyTeam team) {
		if (competition.getSource() == null || !"laliga-fantasy".equalsIgnoreCase(competition.getSource())) {
			return null;
		}
		List<SquadPick> picks = squadPickRepository.findByFantasyTeam_Id(team.getId());
		if (picks.isEmpty()) {
			return null;
		}

		Map<Long, List<SquadPick>> startersByPlayer = new HashMap<>();
		for (SquadPick pick : picks) {
			if (pick.getRole() == null || !"starter".equalsIgnoreCase(pick.getRole())) {
				continue;
			}
			startersByPlayer
					.computeIfAbsent(pick.getPlayer().getId(), ignored -> new ArrayList<>())
					.add(pick);
		}
		if (startersByPlayer.isEmpty()) {
			return null;
		}

		Set<Long> playerIds = startersByPlayer.keySet();
		Set<Long> gameweekIds = startersByPlayer.values().stream()
				.flatMap(List::stream)
				.map(pick -> pick.getGameweek().getId())
				.collect(Collectors.toSet());
		Map<String, BigDecimal> pointsByPair = new HashMap<>();
		if (!playerIds.isEmpty() && !gameweekIds.isEmpty()) {
			for (PlayerGameweekScore score : playerScoreRepository.findByPlayer_IdInAndGameweek_IdIn(
					playerIds, gameweekIds)) {
				pointsByPair.put(
						score.getPlayer().getId() + ":" + score.getGameweek().getId(),
						score.getPoints() != null ? score.getPoints() : BigDecimal.ZERO);
			}
		}

		SquadPick bestPick = null;
		int bestStarts = -1;
		BigDecimal bestPoints = BigDecimal.ZERO;
		for (Map.Entry<Long, List<SquadPick>> entry : startersByPlayer.entrySet()) {
			List<SquadPick> starterWeeks = entry.getValue();
			int starts = starterWeeks.size();
			BigDecimal total = BigDecimal.ZERO;
			SquadPick latest = null;
			for (SquadPick pick : starterWeeks) {
				BigDecimal weekPoints = pointsByPair.getOrDefault(
						pick.getPlayer().getId() + ":" + pick.getGameweek().getId(),
						BigDecimal.ZERO);
				total = total.add(weekPoints);
				if (latest == null
						|| pick.getGameweek().getNumber() > latest.getGameweek().getNumber()) {
					latest = pick;
				}
			}
			if (bestPick == null
					|| starts > bestStarts
					|| (starts == bestStarts && total.compareTo(bestPoints) > 0)) {
				bestStarts = starts;
				bestPoints = total;
				bestPick = latest;
			}
		}
		if (bestPick == null) {
			return null;
		}

		Player player = bestPick.getPlayer();
		String club = clubOf(bestPick);
		String clubExternalId = clubExternalIdOf(bestPick);
		return new TeamViewResponse.LongestServingPlayer(
				player.getId(),
				player.getExternalId(),
				player.getName(),
				PlayerPortraits.url(competition.getSource(), player.getExternalId()),
				player.getPosition(),
				club,
				ClubCrests.url(competition.getSource(), clubExternalId, club),
				shirtNumberOf(bestPick),
				bestStarts,
				bestPoints);
	}

	private List<TeamViewResponse.TransferView> buildTransfers(
			Competition competition,
			FantasyTeam team,
			Gameweek gameweek) {
		List<GameweekTransfer> official = transferRepository
				.findByFantasyTeam_IdAndGameweek_IdOrderBySortOrderAsc(team.getId(), gameweek.getId());
		if (!official.isEmpty()) {
			List<TeamViewResponse.TransferView> views = new ArrayList<>();
			for (GameweekTransfer row : official) {
				if (row.getPlayerIn() != null) {
					views.add(toTransfer("in", competition.getSource(), row.getPlayerIn(), row.getPriceIn(),
							row.getCounterpart()));
				}
				if (row.getPlayerOut() != null) {
					views.add(toTransfer("out", competition.getSource(), row.getPlayerOut(), row.getPriceOut(),
							row.getCounterpart()));
				}
			}
			return views;
		}
		Gameweek previous = previousGameweek(competition.getId(), gameweek.getNumber());
		if (previous == null) {
			return List.of();
		}
		Map<Long, SquadPick> current = indexPicks(
				squadPickRepository.findByFantasyTeam_IdAndGameweek_Id(team.getId(), gameweek.getId()));
		Map<Long, SquadPick> prior = indexPicks(
				squadPickRepository.findByFantasyTeam_IdAndGameweek_Id(team.getId(), previous.getId()));
		List<TeamViewResponse.TransferView> transfers = new ArrayList<>();
		current.forEach((playerId, pick) -> {
			if (!prior.containsKey(playerId)) {
				transfers.add(toTransfer("in", competition.getSource(), pick));
			}
		});
		prior.forEach((playerId, pick) -> {
			if (!current.containsKey(playerId)) {
				transfers.add(toTransfer("out", competition.getSource(), pick));
			}
		});
		transfers.sort(Comparator
				.comparing(TeamViewResponse.TransferView::direction)
				.thenComparing(TeamViewResponse.TransferView::name, Comparator.nullsLast(String::compareToIgnoreCase)));
		return transfers;
	}

	private Gameweek previousGameweek(Long competitionId, Integer number) {
		List<Gameweek> weeks = gameweekRepository.findByCompetition_IdOrderByNumberAsc(competitionId);
		Gameweek previous = null;
		for (Gameweek week : weeks) {
			if (week.getNumber() < number) {
				previous = week;
			}
		}
		return previous;
	}

	private TeamViewResponse.TransferView toTransfer(String direction, String source, SquadPick pick) {
		Player player = pick.getPlayer();
		String club = clubOf(pick);
		String clubExternalId = clubExternalIdOf(pick);
		return new TeamViewResponse.TransferView(
				direction,
				player.getId(),
				player.getExternalId(),
				player.getName(),
				PlayerPortraits.url(source, player.getExternalId()),
				player.getPosition(),
				club,
				ClubCrests.url(source, clubExternalId, club),
				pick.getPrice(),
				null,
				TransferChannels.channel(null));
	}

	private TeamViewResponse.TransferView toTransfer(
			String direction,
			String source,
			Player player,
			BigDecimal price) {
		return toTransfer(direction, source, player, price, null);
	}

	private TeamViewResponse.TransferView toTransfer(
			String direction,
			String source,
			Player player,
			BigDecimal price,
			String counterpart) {
		return new TeamViewResponse.TransferView(
				direction,
				player.getId(),
				player.getExternalId(),
				player.getName(),
				PlayerPortraits.url(source, player.getExternalId()),
				player.getPosition(),
				player.getClub(),
				ClubCrests.url(source, player.getClubExternalId(), player.getClub()),
				price,
				counterpart,
				TransferChannels.channel(counterpart));
	}

	/** Prefer pick-scoped club so club comps and national-team comps stay separate. */
	private static String clubOf(SquadPick pick) {
		if (pick == null) {
			return null;
		}
		if (pick.getClub() != null && !pick.getClub().isBlank()) {
			return pick.getClub();
		}
		return pick.getPlayer() != null ? pick.getPlayer().getClub() : null;
	}

	private static String clubExternalIdOf(SquadPick pick) {
		if (pick == null) {
			return null;
		}
		if (pick.getClubExternalId() != null && !pick.getClubExternalId().isBlank()) {
			return pick.getClubExternalId();
		}
		return pick.getPlayer() != null ? pick.getPlayer().getClubExternalId() : null;
	}

	private static Integer shirtNumberOf(SquadPick pick) {
		if (pick == null) {
			return null;
		}
		if (pick.getShirtNumber() != null) {
			return pick.getShirtNumber();
		}
		return pick.getPlayer() != null ? pick.getPlayer().getShirtNumber() : null;
	}

	private TeamViewResponse.TransferMarketSummary buildTransferMarket(
			Competition competition,
			FantasyTeam team,
			Gameweek gameweek) {
		List<GameweekTransfer> all = transferRepository
				.findByFantasyTeam_IdOrderByGameweek_NumberAscSortOrderAsc(team.getId());
		List<GameweekTransfer> week = all.stream()
				.filter(row -> row.getGameweek().getId().equals(gameweek.getId()))
				.toList();
		return new TeamViewResponse.TransferMarketSummary(
				summarizeMarket(week),
				summarizeMarket(all),
				findMostExpensivePurchase(competition.getSource(), all),
				findHighestSale(competition.getSource(), all));
	}

	private TeamViewResponse.TransferHighlight findMostExpensivePurchase(
			String source,
			List<GameweekTransfer> rows) {
		GameweekTransfer best = null;
		for (GameweekTransfer row : rows) {
			if (row.getPlayerIn() == null || row.getPriceIn() == null) {
				continue;
			}
			if (best == null || row.getPriceIn().compareTo(best.getPriceIn()) > 0) {
				best = row;
			}
		}
		if (best == null) {
			return null;
		}
		return toHighlight(source, best.getPlayerIn(), best.getPriceIn(), best.getCounterpart(), best.getGameweek());
	}

	private TeamViewResponse.TransferHighlight findHighestSale(
			String source,
			List<GameweekTransfer> rows) {
		GameweekTransfer best = null;
		for (GameweekTransfer row : rows) {
			if (row.getPlayerOut() == null || row.getPriceOut() == null) {
				continue;
			}
			if (best == null || row.getPriceOut().compareTo(best.getPriceOut()) > 0) {
				best = row;
			}
		}
		if (best == null) {
			return null;
		}
		return toHighlight(source, best.getPlayerOut(), best.getPriceOut(), best.getCounterpart(), best.getGameweek());
	}

	private TeamViewResponse.TransferHighlight toHighlight(
			String source,
			Player player,
			BigDecimal price,
			String counterpart,
			Gameweek gameweek) {
		return new TeamViewResponse.TransferHighlight(
				player.getId(),
				player.getExternalId(),
				player.getName(),
				PlayerPortraits.url(source, player.getExternalId()),
				player.getPosition(),
				player.getClub(),
				ClubCrests.url(source, player.getClubExternalId(), player.getClub()),
				player.getShirtNumber(),
				price,
				counterpart,
				TransferChannels.channel(counterpart),
				gameweek != null ? gameweek.getNumber() : null,
				gameweek != null ? gameweek.getName() : null);
	}

	private TeamViewResponse.TransferMarketScope summarizeMarket(List<GameweekTransfer> rows) {
		Accumulator soldMarket = new Accumulator();
		Accumulator soldClause = new Accumulator();
		Accumulator boughtMarket = new Accumulator();
		Accumulator boughtClause = new Accumulator();
		Map<String, Accumulator> soldTo = new HashMap<>();
		Map<String, Accumulator> boughtFrom = new HashMap<>();
		for (GameweekTransfer row : rows) {
			if (row.getPlayerOut() != null) {
				boolean market = TransferChannels.isMarket(row.getCounterpart());
				(market ? soldMarket : soldClause).add(row.getPriceOut());
				if (!market) {
					soldTo.computeIfAbsent(row.getCounterpart().strip(), key -> new Accumulator())
							.add(row.getPriceOut());
				}
			}
			if (row.getPlayerIn() != null) {
				boolean market = TransferChannels.isMarket(row.getCounterpart());
				(market ? boughtMarket : boughtClause).add(row.getPriceIn());
				if (!market) {
					boughtFrom.computeIfAbsent(row.getCounterpart().strip(), key -> new Accumulator())
							.add(row.getPriceIn());
				}
			}
		}
		return new TeamViewResponse.TransferMarketScope(
				soldMarket.toGroup(),
				soldClause.toGroup(),
				boughtMarket.toGroup(),
				boughtClause.toGroup(),
				toCounterpartGroups(soldTo),
				toCounterpartGroups(boughtFrom));
	}

	private List<TeamViewResponse.CounterpartGroup> toCounterpartGroups(Map<String, Accumulator> grouped) {
		List<TeamViewResponse.CounterpartGroup> groups = new ArrayList<>();
		for (Map.Entry<String, Accumulator> item : grouped.entrySet()) {
			groups.add(new TeamViewResponse.CounterpartGroup(
					item.getKey(), item.getValue().count, item.getValue().total));
		}
		groups.sort(Comparator
				.comparing((TeamViewResponse.CounterpartGroup group) -> group.total(), Comparator.reverseOrder())
				.thenComparing(TeamViewResponse.CounterpartGroup::name, String.CASE_INSENSITIVE_ORDER));
		return groups;
	}

	private static final class Accumulator {
		private int count;
		private BigDecimal total = BigDecimal.ZERO;

		private void add(BigDecimal amount) {
			count++;
			if (amount != null) {
				total = total.add(amount);
			}
		}

		private TeamViewResponse.DealGroup toGroup() {
			return new TeamViewResponse.DealGroup(count, total);
		}
	}

	private boolean tripleCaptain(Long teamId, Long gameweekId) {
		return teamScoreRepository.findByFantasyTeam_IdAndGameweek_Id(teamId, gameweekId)
				.map(TeamGameweekScore::isTripleCaptain)
				.orElse(false);
	}

	private Comparator<SquadPick> pickComparator() {
		return Comparator
				.comparing((SquadPick pick) -> "starter".equalsIgnoreCase(pick.getRole()) ? 0 : 1)
				.thenComparing(pick -> positionOrder(pick.getPlayer().getPosition()))
				.thenComparing(pick -> pick.getPlayer().getName());
	}

	private int positionOrder(String position) {
		if (position == null) {
			return 9;
		}
		return switch (position.toUpperCase()) {
			case "GK" -> 0;
			case "DEF" -> 1;
			case "MID" -> 2;
			case "FWD" -> 3;
			default -> 8;
		};
	}

	private Map<Long, SquadPick> indexPicks(List<SquadPick> picks) {
		return picks.stream().collect(Collectors.toMap(pick -> pick.getPlayer().getId(), Function.identity()));
	}

	private Map<Long, PlayerGameweekScore> indexScores(List<PlayerGameweekScore> scores) {
		Map<Long, PlayerGameweekScore> map = new HashMap<>();
		for (PlayerGameweekScore score : scores) {
			map.put(score.getPlayer().getId(), score);
		}
		return map;
	}

	private BigDecimal pointsOf(PlayerGameweekScore score) {
		return score != null && score.getPoints() != null ? score.getPoints() : BigDecimal.ZERO;
	}

	private Gameweek resolveGameweek(List<Gameweek> gameweeks, Integer requested) {
		if (requested == null) {
			return gameweeks.get(gameweeks.size() - 1);
		}
		return gameweeks.stream()
				.filter(gw -> gw.getNumber().equals(requested))
				.findFirst()
				.orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Gameweek not found"));
	}

	private Competition requireCompetition(Long id) {
		return competitionRepository.findById(id)
				.orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Competition not found"));
	}

	private FantasyTeam requireTeam(Long competitionId) {
		return fantasyTeamRepository.findByCompetition_Id(competitionId)
				.orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Fantasy team not found"));
	}

	private Gameweek requireGameweek(Long competitionId, Integer number) {
		return gameweekRepository.findByCompetition_IdAndNumber(competitionId, number)
				.orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Gameweek not found"));
	}
}
