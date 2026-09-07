package com.fantasytracker.backend.repositories;

import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.fantasytracker.backend.entities.Competition;

public interface CompetitionRepository extends JpaRepository<Competition, Long> {

	Optional<Competition> findBySourceAndExternalIdAndSeason(String source, String externalId, String season);
}
