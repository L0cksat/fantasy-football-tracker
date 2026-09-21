package com.fantasytracker.backend.services;

import java.util.Map;

public final class ClubCrests {

	private static final String SOFASCORE_TEAM_IMAGE = "https://img.sofascore.com/api/v1/team/%s/image";
	private static final String FPL_BADGE_IMAGE =
			"https://resources.premierleague.com/premierleague/badges/70/t%s.png";

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

	private static final Map<String, String> SOFASCORE_LALIGA_IDS = Map.ofEntries(
			Map.entry("athletic", "2825"),
			Map.entry("athletic club", "2825"),
			Map.entry("athletic bilbao", "2825"),
			Map.entry("atletico", "2836"),
			Map.entry("atletico madrid", "2836"),
			Map.entry("atlético madrid", "2836"),
			Map.entry("barcelona", "2817"),
			Map.entry("fc barcelona", "2817"),
			Map.entry("celta", "2821"),
			Map.entry("celta vigo", "2821"),
			Map.entry("alaves", "2885"),
			Map.entry("alavés", "2885"),
			Map.entry("deportivo alaves", "2885"),
			Map.entry("deportivo alavés", "2885"),
			Map.entry("deportivo", "2832"),
			Map.entry("deportivo de la coruna", "2832"),
			Map.entry("deportivo de la coruña", "2832"),
			Map.entry("elche", "2846"),
			Map.entry("espanyol", "2814"),
			Map.entry("getafe", "2859"),
			Map.entry("levante", "2849"),
			Map.entry("levante ud", "2849"),
			Map.entry("malaga", "2830"),
			Map.entry("málaga", "2830"),
			Map.entry("málaga cf", "2830"),
			Map.entry("osasuna", "2820"),
			Map.entry("rayo", "2818"),
			Map.entry("rayo vallecano", "2818"),
			Map.entry("betis", "2816"),
			Map.entry("real betis", "2816"),
			Map.entry("real madrid", "2829"),
			Map.entry("racing", "2835"),
			Map.entry("racing santander", "2835"),
			Map.entry("real racing club", "2835"),
			Map.entry("real sociedad", "2824"),
			Map.entry("sevilla", "2833"),
			Map.entry("valencia", "2828"),
			Map.entry("villarreal", "2819"),
			// Common misspelling in Official LaLiga Fantasy exports
			Map.entry("villareal", "2819"),
			Map.entry("villarreal cf", "2819"));

	private ClubCrests() {
	}

	public static String url(String source, String clubExternalId, String clubName) {
		if (source != null && "fpl".equalsIgnoreCase(source)) {
			String code = blankToNull(clubExternalId);
			if (code != null && code.chars().allMatch(Character::isDigit)) {
				return FPL_BADGE_IMAGE.formatted(code);
			}
		}
		String id = blankToNull(clubExternalId);
		if (id == null) {
			id = SOFASCORE_LALIGA_IDS.get(normalize(clubName));
		}
		if (id == null && (source == null || "sofascore".equalsIgnoreCase(source) || "fpl".equalsIgnoreCase(source))) {
			id = SOFASCORE_PREMIER_LEAGUE_IDS.get(normalize(clubName));
		}
		if (id != null && !id.chars().allMatch(Character::isDigit)) {
			return null;
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
