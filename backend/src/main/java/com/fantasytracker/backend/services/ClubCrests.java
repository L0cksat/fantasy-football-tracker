package com.fantasytracker.backend.services;

import java.util.Map;

public final class ClubCrests {

	private static final String SOFASCORE_TEAM_IMAGE = "https://img.sofascore.com/api/v1/team/%s/image";

	private static final Map<String, String> SOFASCORE_PREMIER_LEAGUE_IDS = Map.ofEntries(
			Map.entry("arsenal", "42"),
			Map.entry("aston villa", "40"),
			Map.entry("bournemouth", "60"),
			Map.entry("afc bournemouth", "60"),
			Map.entry("brentford", "50"),
			Map.entry("brighton", "30"),
			Map.entry("brighton and hove albion", "30"),
			Map.entry("burnley", "6"),
			Map.entry("chelsea", "38"),
			Map.entry("crystal palace", "7"),
			Map.entry("everton", "48"),
			Map.entry("fulham", "43"),
			Map.entry("ipswich", "32"),
			Map.entry("ipswich town", "32"),
			Map.entry("leeds", "34"),
			Map.entry("leeds united", "34"),
			Map.entry("liverpool", "44"),
			Map.entry("liverpool fc", "44"),
			Map.entry("man city", "17"),
			Map.entry("manchester city", "17"),
			Map.entry("man united", "35"),
			Map.entry("manchester united", "35"),
			Map.entry("newcastle", "39"),
			Map.entry("newcastle united", "39"),
			Map.entry("nottingham forest", "14"),
			Map.entry("nottm forest", "14"),
			Map.entry("sunderland", "41"),
			Map.entry("tottenham", "33"),
			Map.entry("tottenham hotspur", "33"),
			Map.entry("west ham", "37"),
			Map.entry("west ham united", "37"),
			Map.entry("wolves", "3"),
			Map.entry("wolverhampton", "3"),
			Map.entry("wolverhampton wanderers", "3"),
			Map.entry("hull", "96"),
			Map.entry("hull city", "96"));

	private ClubCrests() {
	}

	public static String url(String source, String clubExternalId, String clubName) {
		String id = blankToNull(clubExternalId);
		if (id == null && (source == null || "sofascore".equalsIgnoreCase(source))) {
			id = SOFASCORE_PREMIER_LEAGUE_IDS.get(normalize(clubName));
		}
		if (id == null) {
			return null;
		}
		return SOFASCORE_TEAM_IMAGE.formatted(id);
	}

	private static String blankToNull(String value) {
		return value == null || value.isBlank() ? null : value.trim();
	}

	private static String normalize(String clubName) {
		if (clubName == null) {
			return "";
		}
		return clubName.strip().toLowerCase()
				.replace(".", "")
				.replace("&", "and")
				.replaceAll("\\s+", " ");
	}
}
