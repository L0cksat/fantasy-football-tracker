package com.fantasytracker.backend.repositories;

import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.fantasytracker.backend.entities.FantasyTeam;

public interface FantasyTeamRepository extends JpaRepository<FantasyTeam, Long> {

	Optional<FantasyTeam> findByCompetition_Id(Long competitionId);
}
