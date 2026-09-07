package com.fantasytracker.backend.config;

import java.io.InputStream;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import com.fantasytracker.backend.dto.SnapshotRequest;
import com.fantasytracker.backend.repositories.CompetitionRepository;
import com.fantasytracker.backend.services.IngestService;
import com.fasterxml.jackson.databind.ObjectMapper;

@Component
@ConditionalOnProperty(name = "fantasy.seed.enabled", havingValue = "true", matchIfMissing = true)
public class SeedRunner implements ApplicationRunner {

	private static final Logger log = LoggerFactory.getLogger(SeedRunner.class);
	private static final String[] SEED_FILES = { "seed/pl-gw1.json", "seed/pl-gw2.json" };

	private final CompetitionRepository competitionRepository;
	private final IngestService ingestService;
	private final ObjectMapper objectMapper;

	public SeedRunner(
			CompetitionRepository competitionRepository,
			IngestService ingestService,
			ObjectMapper objectMapper) {
		this.competitionRepository = competitionRepository;
		this.ingestService = ingestService;
		this.objectMapper = objectMapper;
	}

	@Override
	public void run(ApplicationArguments args) throws Exception {
		if (competitionRepository.count() > 0) {
			return;
		}
		for (String path : SEED_FILES) {
			try (InputStream input = new ClassPathResource(path).getInputStream()) {
				SnapshotRequest snapshot = objectMapper.readValue(input, SnapshotRequest.class);
				ingestService.upsertSnapshot(snapshot);
				log.info("Seeded {}", path);
			}
		}
	}
}
