package com.fantasytracker.backend.services;

import java.util.Map;

public final class CompetitionBranding {

	private static final String SOFASCORE_TOURNAMENT_IMAGE =
			"https://img.sofascore.com/api/v1/unique-tournament/%s/image";
	private static final String SOFASCORE_TOURNAMENT_DARK_IMAGE =
			"https://img.sofascore.com/api/v1/unique-tournament/%s/image/dark";
	private static final String SOFASCORE_CATEGORY_IMAGE =
			"https://img.sofascore.com/api/v1/category/%s/image";

	private static final Map<String, Country> SOFASCORE_COUNTRIES = Map.ofEntries(
			Map.entry("17", new Country("England", "1")),
			Map.entry("8", new Country("Spain", "32")),
			Map.entry("23", new Country("Italy", "31")),
			Map.entry("34", new Country("France", "7")),
			Map.entry("35", new Country("Germany", "30")),
			Map.entry("7", new Country("Europe", "1465")),
			Map.entry("679", new Country("Europe", "1465")),
			Map.entry("242", new Country("USA", "26")),
			Map.entry("325", new Country("Brazil", "13")),
			Map.entry("1044", new Country("England", "1")));

	private static final Map<String, Colors> SOFASCORE_COLORS = Map.ofEntries(
			Map.entry("17", new Colors("#3c1c5a", "#f80158")),
			Map.entry("8", new Colors("#2f4a89", "#f4a32e")),
			Map.entry("23", new Colors("#09519e", "#008fd7")),
			Map.entry("34", new Colors("#091c3e", "#a9c011")),
			Map.entry("35", new Colors("#e2080e", "#8e0902")),
			Map.entry("7", new Colors("#062b5c", "#086aab")),
			Map.entry("679", new Colors("#3d1a08", "#f37d25")),
			Map.entry("242", new Colors("#e2231a", "#062f69")),
			Map.entry("325", new Colors("#C7FF00", "#969696")),
			Map.entry("1044", new Colors("#06121e", "#00c2cb")));

	private CompetitionBranding() {
	}

	public static String logoUrl(String source, String externalId) {
		String id = brandingTournamentId(source, externalId);
		if (id == null) {
			return null;
		}
		return SOFASCORE_TOURNAMENT_IMAGE.formatted(id);
	}

	public static String logoDarkUrl(String source, String externalId) {
		String id = brandingTournamentId(source, externalId);
		if (id == null) {
			return null;
		}
		return SOFASCORE_TOURNAMENT_DARK_IMAGE.formatted(id);
	}

	public static String flagUrl(String source, String externalId) {
		Country country = country(source, externalId);
		if (country == null) {
			return null;
		}
		return SOFASCORE_CATEGORY_IMAGE.formatted(country.categoryId());
	}

	public static String countryName(String source, String externalId) {
		Country country = country(source, externalId);
		return country == null ? null : country.name();
	}

	public static String primaryColor(String source, String externalId) {
		Colors colors = colors(source, externalId);
		return colors == null ? null : colors.primary();
	}

	public static String secondaryColor(String source, String externalId) {
		Colors colors = colors(source, externalId);
		return colors == null ? null : colors.secondary();
	}

	private static Country country(String source, String externalId) {
		String id = brandingTournamentId(source, externalId);
		if (id == null) {
			return null;
		}
		return SOFASCORE_COUNTRIES.get(id);
	}

	private static Colors colors(String source, String externalId) {
		String id = brandingTournamentId(source, externalId);
		if (id == null) {
			return null;
		}
		return SOFASCORE_COLORS.get(id);
	}

	private static String brandingTournamentId(String source, String externalId) {
		if (source != null && "laliga-fantasy".equalsIgnoreCase(source)) {
			return "8";
		}
		if (source != null && "fpl".equalsIgnoreCase(source)) {
			return "17";
		}
		if (source != null && "wsl".equalsIgnoreCase(source)) {
			return "1044";
		}
		return numericId(source, externalId);
	}

	private static String numericId(String source, String externalId) {
		if (source == null || !"sofascore".equalsIgnoreCase(source)) {
			return null;
		}
		if (externalId == null || externalId.isBlank() || !externalId.chars().allMatch(Character::isDigit)) {
			return null;
		}
		return externalId.trim();
	}

	private record Country(String name, String categoryId) {
	}

	private record Colors(String primary, String secondary) {
	}
}
