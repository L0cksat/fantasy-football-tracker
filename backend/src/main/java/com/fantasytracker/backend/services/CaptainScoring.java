package com.fantasytracker.backend.services;

import java.math.BigDecimal;

public final class CaptainScoring {

	private CaptainScoring() {
	}

	public static int multiplier(boolean captain, boolean tripleCaptain) {
		if (!captain) {
			return 1;
		}
		return tripleCaptain ? 3 : 2;
	}

	public static BigDecimal effective(BigDecimal raw, boolean captain, boolean tripleCaptain) {
		BigDecimal base = raw != null ? raw : BigDecimal.ZERO;
		return base.multiply(BigDecimal.valueOf(multiplier(captain, tripleCaptain)));
	}
}
