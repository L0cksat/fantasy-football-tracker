package com.fantasytracker.backend.repositories;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.fantasytracker.backend.entities.Gameweek;

public interface GameweekRepository extends JpaRepository<Gameweek, Long> {

	Optional<Gameweek> findByCompetition_IdAndNumber(Long competitionId, Integer number);

	List<Gameweek> findByCompetition_IdOrderByNumberAsc(Long competitionId);
}
