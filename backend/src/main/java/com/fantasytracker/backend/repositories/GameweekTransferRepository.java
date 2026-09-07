package com.fantasytracker.backend.repositories;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

import com.fantasytracker.backend.entities.GameweekTransfer;

public interface GameweekTransferRepository extends JpaRepository<GameweekTransfer, Long> {

	List<GameweekTransfer> findByFantasyTeam_IdAndGameweek_IdOrderBySortOrderAsc(Long fantasyTeamId, Long gameweekId);

	void deleteByFantasyTeam_IdAndGameweek_Id(Long fantasyTeamId, Long gameweekId);
}
