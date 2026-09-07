package com.fantasytracker.backend.services;

public final class PlayerPortraits {

	private static final String SOFASCORE_PLAYER_IMAGE = "https://img.sofascore.com/api/v1/player/%s/image";

	private PlayerPortraits() {
	}

	public static String url(String source, String externalId) {
		if (source == null || !"sofascore".equalsIgnoreCase(source)) {
			return null;
		}
		if (externalId == null || externalId.isBlank() || !externalId.chars().allMatch(Character::isDigit)) {
			return null;
		}
		return SOFASCORE_PLAYER_IMAGE.formatted(externalId.trim());
	}
}
