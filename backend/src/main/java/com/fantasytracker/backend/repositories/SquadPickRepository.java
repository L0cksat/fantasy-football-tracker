package com.fantasytracker.backend.repositories;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.fantasytracker.backend.entities.SquadPick;

public interface SquadPickRepository extends JpaRepository<SquadPick, Long> {

	List<SquadPick> findByFantasyTeam_IdAndGameweek_Id(Long fantasyTeamId, Long gameweekId);

	List<SquadPick> findByFantasyTeam_Id(Long fantasyTeamId);

	Optional<SquadPick> findByFantasyTeam_IdAndPlayer_IdAndGameweek_Id(
			Long fantasyTeamId, Long playerId, Long gameweekId);

	void deleteByPlayer_Id(Long playerId);
}
