package com.fantasytracker.backend.repositories;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.fantasytracker.backend.entities.PlayerGameweekScore;

public interface PlayerGameweekScoreRepository extends JpaRepository<PlayerGameweekScore, Long> {

	Optional<PlayerGameweekScore> findByPlayer_IdAndGameweek_Id(Long playerId, Long gameweekId);

	List<PlayerGameweekScore> findByGameweek_IdAndPlayer_IdIn(Long gameweekId, Collection<Long> playerIds);

	void deleteByPlayer_Id(Long playerId);
}
