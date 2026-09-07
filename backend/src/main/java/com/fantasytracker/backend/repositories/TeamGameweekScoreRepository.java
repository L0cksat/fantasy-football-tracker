package com.fantasytracker.backend.repositories;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.fantasytracker.backend.entities.TeamGameweekScore;

public interface TeamGameweekScoreRepository extends JpaRepository<TeamGameweekScore, Long> {

	Optional<TeamGameweekScore> findByFantasyTeam_IdAndGameweek_Id(Long fantasyTeamId, Long gameweekId);

	List<TeamGameweekScore> findByFantasyTeam_IdOrderByGameweek_NumberAsc(Long fantasyTeamId);
}
