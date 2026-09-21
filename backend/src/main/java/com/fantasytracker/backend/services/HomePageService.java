package com.fantasytracker.backend.services;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.fantasytracker.backend.dto.HomePageResponse;
import com.fantasytracker.backend.dto.HomePageResponse.LeagueBrand;
import com.fantasytracker.backend.dto.HomePageResponse.LeagueStanding;
import com.fantasytracker.backend.dto.HomePageResponse.PlayerOfTheWeek;
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
import com.fantasytracker.backend.repositories.TeamGameweekScoreRepository;

@Service
@Transactional
public class HomePageService {

	private final CompetitionRepository competitionRepository;
	private final FantasyTeamRepository fantasyTeamRepository;
	private final GameweekRepository gameweekRepository;
	private final TeamGameweekScoreRepository teamScoreRepository;
	private final SquadPickRepository squadPickRepository;
	private final PlayerGameweekScoreRepository playerScoreRepository;

	public HomePageService(
			CompetitionRepository competitionRepository,
			FantasyTeamRepository fantasyTeamRepository,
			GameweekRepository gameweekRepository,
			TeamGameweekScoreRepository teamScoreRepository,
			SquadPickRepository squadPickRepository,
			PlayerGameweekScoreRepository playerScoreRepository) {
		this.competitionRepository = competitionRepository;
		this.fantasyTeamRepository = fantasyTeamRepository;
		this.gameweekRepository = gameweekRepository;
		this.teamScoreRepository = teamScoreRepository;
		this.squadPickRepository = squadPickRepository;
		this.playerScoreRepository = playerScoreRepository;
	}

	public HomePageResponse homePage() {
		List<Competition> competitions = competitionRepository.findAll().stream()
				.sorted(Comparator.comparing(Competition::getId))
				.toList();

		Long defaultId = null;
		String defaultSlug = "premier-league";
		for (Competition competition : competitions) {
			if ("premier-league".equals(competition.getSlug())) {
				defaultId = competition.getId();
				defaultSlug = competition.getSlug();
				break;
			}
		}
		if (defaultId == null && !competitions.isEmpty()) {
			defaultId = competitions.get(0).getId();
			defaultSlug = competitions.get(0).getSlug();
		}

		Map<String, LeagueBrand> brands = new LinkedHashMap<>();
		List<PlayerOfTheWeek> potw = new ArrayList<>();
		List<LeagueStanding> weekly = new ArrayList<>();
		List<LeagueStanding> europe = new ArrayList<>();
		List<LeagueStanding> americas = new ArrayList<>();

		for (Competition competition : competitions) {
			String brandKey = CompetitionBranding.brandKey(competition.getSource(), competition.getExternalId());
			if (brandKey != null) {
				brands.putIfAbsent(
						brandKey,
						new LeagueBrand(
								brandKey,
								displayBrandName(brandKey, competition.getName()),
								CompetitionBranding.logoUrl(competition.getSource(), competition.getExternalId()),
								CompetitionBranding.logoDarkUrl(competition.getSource(), competition.getExternalId()),
								CompetitionBranding.primaryColor(competition.getSource(), competition.getExternalId()),
								CompetitionBranding.secondaryColor(
										competition.getSource(), competition.getExternalId())));
			}

			PlayerOfTheWeek winner = playerOfTheWeek(competition);
			if (winner != null) {
				potw.add(winner);
			}

			FantasyTeam team = fantasyTeamRepository.findByCompetition_Id(competition.getId()).orElse(null);
			if (team == null) {
				continue;
			}

			LeagueStanding weekRow = latestWeekStanding(competition, team);
			if (weekRow != null) {
				weekly.add(weekRow);
			}

			LeagueStanding seasonRow = seasonTotalStanding(competition, team);
			if (seasonRow == null) {
				continue;
			}
			if (CompetitionBranding.isAmericas(competition.getSource(), competition.getExternalId())) {
				americas.add(seasonRow);
			} else {
				europe.add(seasonRow);
			}
		}

		return new HomePageResponse(
				defaultId,
				defaultSlug,
				List.copyOf(brands.values()),
				List.copyOf(potw),
				rankStandings(weekly),
				rankStandings(europe),
				rankStandings(americas));
	}

	private LeagueStanding latestWeekStanding(Competition competition, FantasyTeam team) {
		Gameweek gameweek = resolveLatestScoredGameweek(team.getId(), competition.getId());
		if (gameweek == null) {
			return null;
		}
		BigDecimal points = teamScoreRepository
				.findByFantasyTeam_IdAndGameweek_Id(team.getId(), gameweek.getId())
				.map(TeamGameweekScore::getPoints)
				.orElse(BigDecimal.ZERO);
		return standing(competition, gameweek.getNumber(), gameweek.getName(), points);
	}

	private LeagueStanding seasonTotalStanding(Competition competition, FantasyTeam team) {
		List<TeamGameweekScore> scores =
				teamScoreRepository.findByFantasyTeam_IdOrderByGameweek_NumberAsc(team.getId());
		if (scores.isEmpty()) {
			return null;
		}
		BigDecimal total = BigDecimal.ZERO;
		for (TeamGameweekScore score : scores) {
			if (!isScoringComplete(score.getGameweek(), score)) {
				continue;
			}
			if (score.getPoints() != null) {
				total = total.add(score.getPoints());
			}
		}
		return standing(competition, null, null, total);
	}

	private static LeagueStanding standing(
			Competition competition,
			Integer gameweek,
			String gameweekName,
			BigDecimal points) {
		String logo = CompetitionBranding.logoDarkUrl(competition.getSource(), competition.getExternalId());
		if (logo == null) {
			logo = CompetitionBranding.logoUrl(competition.getSource(), competition.getExternalId());
		}
		return new LeagueStanding(
				0,
				competition.getId(),
				competition.getName(),
				competition.getSlug(),
				logo,
				CompetitionBranding.primaryColor(competition.getSource(), competition.getExternalId()),
				CompetitionBranding.secondaryColor(competition.getSource(), competition.getExternalId()),
				gameweek,
				gameweekName,
				points != null ? points : BigDecimal.ZERO);
	}

	private static List<LeagueStanding> rankStandings(List<LeagueStanding> rows) {
		List<LeagueStanding> sorted = rows.stream()
				.sorted(Comparator
						.comparing(LeagueStanding::points, Comparator.nullsLast(Comparator.reverseOrder()))
						.thenComparing(LeagueStanding::competitionId))
				.toList();
		List<LeagueStanding> ranked = new ArrayList<>(sorted.size());
		for (int i = 0; i < sorted.size(); i++) {
			LeagueStanding row = sorted.get(i);
			ranked.add(new LeagueStanding(
					i + 1,
					row.competitionId(),
					row.competitionName(),
					row.competitionSlug(),
					row.logoUrl(),
					row.primaryColor(),
					row.secondaryColor(),
					row.gameweek(),
					row.gameweekName(),
					row.points()));
		}
		return List.copyOf(ranked);
	}

	private PlayerOfTheWeek playerOfTheWeek(Competition competition) {
		FantasyTeam team = fantasyTeamRepository.findByCompetition_Id(competition.getId()).orElse(null);
		if (team == null) {
			return null;
		}
		Gameweek gameweek = resolveLatestScoredGameweek(team.getId(), competition.getId());
		if (gameweek == null) {
			return null;
		}
		TeamGameweekScore teamScore = teamScoreRepository
				.findByFantasyTeam_IdAndGameweek_Id(team.getId(), gameweek.getId())
				.orElse(null);
		boolean tripleCaptain = teamScore != null && teamScore.isTripleCaptain();
		List<SquadPick> picks =
				squadPickRepository.findByFantasyTeam_IdAndGameweek_Id(team.getId(), gameweek.getId());
		if (picks.isEmpty()) {
			return null;
		}

		List<Long> playerIds = picks.stream().map(pick -> pick.getPlayer().getId()).toList();
		Map<Long, PlayerGameweekScore> byPlayer = playerScoreRepository
				.findByGameweek_IdAndPlayer_IdIn(gameweek.getId(), playerIds)
				.stream()
				.collect(java.util.stream.Collectors.toMap(score -> score.getPlayer().getId(), score -> score));

		SquadPick bestPick = null;
		BigDecimal bestPoints = null;
		for (SquadPick pick : picks) {
			PlayerGameweekScore score = byPlayer.get(pick.getPlayer().getId());
			BigDecimal raw = score != null && score.getPoints() != null ? score.getPoints() : BigDecimal.ZERO;
			BigDecimal effective = CaptainScoring.effective(raw, pick.isCaptain(), tripleCaptain);
			if (bestPoints == null || effective.compareTo(bestPoints) > 0) {
				bestPoints = effective;
				bestPick = pick;
			}
		}
		if (bestPick == null || bestPoints == null) {
			return null;
		}

		Player player = bestPick.getPlayer();
		String club = bestPick.getClub() != null && !bestPick.getClub().isBlank()
				? bestPick.getClub()
				: player.getClub();
		String clubExternalId = bestPick.getClubExternalId() != null && !bestPick.getClubExternalId().isBlank()
				? bestPick.getClubExternalId()
				: player.getClubExternalId();
		Integer shirtNumber = bestPick.getShirtNumber() != null
				? bestPick.getShirtNumber()
				: player.getShirtNumber();
		String logo = CompetitionBranding.logoDarkUrl(competition.getSource(), competition.getExternalId());
		if (logo == null) {
			logo = CompetitionBranding.logoUrl(competition.getSource(), competition.getExternalId());
		}

		return new PlayerOfTheWeek(
				competition.getId(),
				competition.getName(),
				competition.getSlug(),
				logo,
				CompetitionBranding.primaryColor(competition.getSource(), competition.getExternalId()),
				CompetitionBranding.secondaryColor(competition.getSource(), competition.getExternalId()),
				gameweek.getNumber(),
				gameweek.getName(),
				player.getId(),
				player.getExternalId(),
				player.getName(),
				shirtNumber,
				player.getPosition(),
				club,
				PlayerPortraits.url(competition.getSource(), player.getExternalId()),
				ClubCrests.url(competition.getSource(), clubExternalId, club),
				bestPoints);
	}

	/**
	 * Prefer the latest week that has finished scoring and has a squad.
	 * SofaScore often leaves prior rounds as {@code live} until finalized, so weeks with
	 * points &gt; 0 count as complete even when status is still live.
	 */
	private Gameweek resolveLatestScoredGameweek(Long teamId, Long competitionId) {
		List<Gameweek> weeks = gameweekRepository.findByCompetition_IdOrderByNumberAsc(competitionId);
		List<TeamGameweekScore> scores =
				teamScoreRepository.findByFantasyTeam_IdOrderByGameweek_NumberAsc(teamId);
		Map<Long, TeamGameweekScore> scoreByWeekId = scores.stream()
				.collect(java.util.stream.Collectors.toMap(
						score -> score.getGameweek().getId(),
						score -> score,
						(left, right) -> right));

		for (int i = weeks.size() - 1; i >= 0; i--) {
			Gameweek week = weeks.get(i);
			if (squadPickRepository.findByFantasyTeam_IdAndGameweek_Id(teamId, week.getId()).isEmpty()) {
				continue;
			}
			if (isScoringComplete(week, scoreByWeekId.get(week.getId()))) {
				return week;
			}
		}
		for (int i = scores.size() - 1; i >= 0; i--) {
			TeamGameweekScore score = scores.get(i);
			if (score.getPoints() != null && score.getPoints().compareTo(BigDecimal.ZERO) > 0) {
				return score.getGameweek();
			}
		}
		if (!scores.isEmpty()) {
			return scores.get(scores.size() - 1).getGameweek();
		}
		return null;
	}

	/** Finished status, or any week that already posted points (incomplete open shells stay out). */
	private static boolean isScoringComplete(Gameweek week, TeamGameweekScore score) {
		if (week.getStatus() != null && "finished".equalsIgnoreCase(week.getStatus())) {
			return true;
		}
		return score != null && score.getPoints() != null && score.getPoints().compareTo(BigDecimal.ZERO) > 0;
	}

	private static String displayBrandName(String brandKey, String fallback) {
		return switch (brandKey) {
			case "17" -> "Premier League";
			case "8" -> "LaLiga";
			case "23" -> "Serie A";
			case "34" -> "Ligue 1";
			case "35" -> "Bundesliga";
			case "7" -> "Champions League";
			case "679" -> "Europa League";
			case "10783" -> "Nations League";
			case "242" -> "MLS";
			case "325" -> "Brasileirão";
			case "1044" -> "WSL";
			default -> fallback;
		};
	}
}
