package com.fantasytracker.backend.services;

public final class TransferChannels {

	public static final String MARKET = "market";
	public static final String RELEASE_CLAUSE = "release-clause";

	private TransferChannels() {
	}

	public static boolean isMarket(String counterpart) {
		return counterpart == null || counterpart.isBlank() || "market".equalsIgnoreCase(counterpart.strip());
	}

	public static String channel(String counterpart) {
		return isMarket(counterpart) ? MARKET : RELEASE_CLAUSE;
	}
}
