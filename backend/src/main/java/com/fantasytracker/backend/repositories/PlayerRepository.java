package com.fantasytracker.backend.repositories;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.fantasytracker.backend.entities.Player;

public interface PlayerRepository extends JpaRepository<Player, Long> {

	Optional<Player> findBySourceAndExternalId(String source, String externalId);

	List<Player> findByExternalIdStartingWith(String prefix);
}
