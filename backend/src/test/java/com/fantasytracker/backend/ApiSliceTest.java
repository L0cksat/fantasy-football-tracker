package com.fantasytracker.backend;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.nio.charset.StandardCharsets;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.core.io.ClassPathResource;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class ApiSliceTest {

	@Autowired
	private MockMvc mockMvc;

	@BeforeEach
	void ingestSeedWeeks() throws Exception {
		ingest("seed/pl-gw1.json");
		ingest("seed/pl-gw2.json");
	}

	@Test
	void competitionsTeamCompareAndTotals() throws Exception {
		mockMvc.perform(get("/api/v1/competitions"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$[0].name").value("Premier League"))
				.andExpect(jsonPath("$[0].teamName").value("Sofa Saints"))
				.andExpect(jsonPath("$[0].primaryColor").value("#3c1c5a"))
				.andExpect(jsonPath("$[0].secondaryColor").value("#f80158"))
				.andExpect(jsonPath("$[0].logoDarkUrl")
						.value("https://img.sofascore.com/api/v1/unique-tournament/17/image/dark"))
				.andExpect(jsonPath("$[0].gameweeks[0]").value(1))
				.andExpect(jsonPath("$[0].gameweeks[1]").value(2));

		mockMvc.perform(get("/api/v1/competitions/1/team").param("gameweek", "1"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.competition.logoUrl")
						.value("https://img.sofascore.com/api/v1/unique-tournament/17/image"))
				.andExpect(jsonPath("$.competition.logoDarkUrl")
						.value("https://img.sofascore.com/api/v1/unique-tournament/17/image/dark"))
				.andExpect(jsonPath("$.competition.flagUrl")
						.value("https://img.sofascore.com/api/v1/category/1/image"))
				.andExpect(jsonPath("$.competition.countryName").value("England"))
				.andExpect(jsonPath("$.competition.primaryColor").value("#3c1c5a"))
				.andExpect(jsonPath("$.competition.secondaryColor").value("#f80158"))
				.andExpect(jsonPath("$.teamPoints").value(71.0))
				.andExpect(jsonPath("$.picks.length()").value(15))
				.andExpect(jsonPath("$.tripleCaptain").value(false))
				.andExpect(jsonPath("$.picks[?(@.captain==true)].name").value(org.hamcrest.Matchers.hasItem("Mohamed Salah")))
				.andExpect(jsonPath("$.picks[?(@.captain==true)].points").value(org.hamcrest.Matchers.hasItem(28.0)))
				.andExpect(jsonPath("$.picks[?(@.captain==true)].basePoints").value(org.hamcrest.Matchers.hasItem(14.0)))
				.andExpect(jsonPath("$.picks[?(@.name=='Mohamed Salah')].clubCrestUrl")
						.value(org.hamcrest.Matchers.hasItem("https://img.sofascore.com/api/v1/team/44/image")));

		mockMvc.perform(get("/api/v1/competitions/1/gameweeks/2"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.gameweek.number").value(2))
				.andExpect(jsonPath("$.teamPoints").value(83.0))
				.andExpect(jsonPath("$.transfers.length()").value(0));

		mockMvc.perform(get("/api/v1/competitions/1/compare").param("from", "1").param("to", "2"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.teamFromPoints").value(71.0))
				.andExpect(jsonPath("$.teamToPoints").value(83.0))
				.andExpect(jsonPath("$.teamDelta").value(12.0))
				.andExpect(jsonPath("$.players[?(@.name=='Erling Haaland')].delta").value(org.hamcrest.Matchers.hasItem(11.0)));

		mockMvc.perform(get("/api/v1/competitions/1/totals"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.totalPoints").value(154.0))
				.andExpect(jsonPath("$.gameweeks.length()").value(2));
	}

	@Test
	void ingestReplacesPreviousSquadForTheSameGameweek() throws Exception {
		String replacement = """
				{
				  "competition": {
				    "source": "sofascore",
				    "externalId": "17",
				    "name": "Premier League",
				    "season": "2026/27",
				    "slug": "premier-league"
				  },
				  "gameweek": { "number": 1, "name": "GW1", "status": "finished" },
				  "team": { "name": "The Inbetweeners FC", "managerName": "Locksat" },
				  "teamPoints": 12,
				  "picks": [
				    {
				      "player": { "externalId": "975079", "name": "Joao Pedro", "position": "FWD", "club": "Chelsea" },
				      "role": "starter",
				      "captain": true,
				      "viceCaptain": false,
				      "points": 12,
				      "rating": 7.5,
				      "breakdown": {}
				    }
				  ]
				}
				""";
		mockMvc.perform(post("/api/v1/ingest/snapshots")
						.contentType(MediaType.APPLICATION_JSON)
						.content(replacement))
				.andExpect(status().isCreated());

		mockMvc.perform(get("/api/v1/competitions/1/team").param("gameweek", "1"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.team.name").value("The Inbetweeners FC"))
				.andExpect(jsonPath("$.picks.length()").value(1))
				.andExpect(jsonPath("$.picks[0].name").value("Joao Pedro"))
				.andExpect(jsonPath("$.picks[0].externalId").value("975079"))
				.andExpect(jsonPath("$.picks[0].points").value(24.0))
				.andExpect(jsonPath("$.picks[0].captainMultiplier").value(2))
				.andExpect(jsonPath("$.picks[0].playerPortraitUrl")
						.value("https://img.sofascore.com/api/v1/player/975079/image"));
	}

	@Test
	void tripleCaptainTriplesDisplayedCaptainPoints() throws Exception {
		String triple = """
				{
				  "competition": {
				    "source": "sofascore",
				    "externalId": "17",
				    "name": "Premier League",
				    "season": "2026/27",
				    "slug": "premier-league"
				  },
				  "gameweek": { "number": 1, "name": "GW1", "status": "finished" },
				  "team": { "name": "The Inbetweeners FC", "managerName": "Locksat" },
				  "teamPoints": 15,
				  "tripleCaptain": true,
				  "picks": [
				    {
				      "player": { "externalId": "975079", "name": "Joao Pedro", "position": "FWD", "club": "Chelsea" },
				      "role": "starter",
				      "captain": true,
				      "viceCaptain": false,
				      "points": 5,
				      "rating": 7.5,
				      "breakdown": {}
				    }
				  ]
				}
				""";
		mockMvc.perform(post("/api/v1/ingest/snapshots")
						.contentType(MediaType.APPLICATION_JSON)
						.content(triple))
				.andExpect(status().isCreated());

		mockMvc.perform(get("/api/v1/competitions/1/team").param("gameweek", "1"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.tripleCaptain").value(true))
				.andExpect(jsonPath("$.teamPoints").value(15.0))
				.andExpect(jsonPath("$.picks[0].basePoints").value(5.0))
				.andExpect(jsonPath("$.picks[0].points").value(15.0))
				.andExpect(jsonPath("$.picks[0].captainMultiplier").value(3));
	}

	@Test
	void teamViewShowsTransfersWhenSquadChanges() throws Exception {
		String week1 = """
				{
				  "competition": {
				    "source": "sofascore",
				    "externalId": "17-transfers",
				    "name": "Premier League Transfers",
				    "season": "2026/27",
				    "slug": "premier-league-transfers"
				  },
				  "gameweek": { "number": 1, "name": "GW1", "status": "finished" },
				  "team": { "name": "Transfer FC", "managerName": "Locksat" },
				  "teamPoints": 10,
				  "picks": [
				    {
				      "player": { "externalId": "100", "name": "Kaoru Mitoma", "position": "MID", "club": "Brighton" },
				      "role": "starter",
				      "captain": false,
				      "viceCaptain": false,
				      "points": 5,
				      "price": 5.0,
				      "rating": 7.0,
				      "breakdown": {}
				    },
				    {
				      "player": { "externalId": "101", "name": "Cole Palmer", "position": "MID", "club": "Chelsea" },
				      "role": "starter",
				      "captain": true,
				      "viceCaptain": false,
				      "points": 8,
				      "price": 8.0,
				      "rating": 7.5,
				      "breakdown": {}
				    }
				  ]
				}
				""";
		String week2 = """
				{
				  "competition": {
				    "source": "sofascore",
				    "externalId": "17-transfers",
				    "name": "Premier League Transfers",
				    "season": "2026/27",
				    "slug": "premier-league-transfers"
				  },
				  "gameweek": { "number": 2, "name": "GW2", "status": "finished" },
				  "team": { "name": "Transfer FC", "managerName": "Locksat" },
				  "teamPoints": 12,
				  "transferPenalty": 5,
				  "picks": [
				    {
				      "player": { "externalId": "102", "name": "Marcelino Nunez", "position": "MID", "club": "Ipswich Town" },
				      "role": "starter",
				      "captain": false,
				      "viceCaptain": false,
				      "points": 4,
				      "price": 4.0,
				      "rating": 6.8,
				      "breakdown": {}
				    },
				    {
				      "player": { "externalId": "101", "name": "Cole Palmer", "position": "MID", "club": "Chelsea" },
				      "role": "starter",
				      "captain": true,
				      "viceCaptain": false,
				      "points": 8,
				      "price": 8.1,
				      "rating": 7.6,
				      "breakdown": {}
				    }
				  ]
				}
				""";
		String created = mockMvc.perform(post("/api/v1/ingest/snapshots")
						.contentType(MediaType.APPLICATION_JSON)
						.content(week1))
				.andExpect(status().isCreated())
				.andReturn()
				.getResponse()
				.getContentAsString();
		mockMvc.perform(post("/api/v1/ingest/snapshots")
						.contentType(MediaType.APPLICATION_JSON)
						.content(week2))
				.andExpect(status().isCreated());

		int competitionId = new com.fasterxml.jackson.databind.ObjectMapper().readTree(created).get("competitionId").asInt();
		mockMvc.perform(get("/api/v1/competitions/" + competitionId + "/team").param("gameweek", "2"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.transferPenalty").value(5.0))
				.andExpect(jsonPath("$.transfers.length()").value(2))
				.andExpect(jsonPath("$.transfers[?(@.direction=='in')].name").value(org.hamcrest.Matchers.hasItem("Marcelino Nunez")))
				.andExpect(jsonPath("$.transfers[?(@.direction=='in')].price").value(org.hamcrest.Matchers.hasItem(4.0)))
				.andExpect(jsonPath("$.transfers[?(@.direction=='out')].name").value(org.hamcrest.Matchers.hasItem("Kaoru Mitoma")))
				.andExpect(jsonPath("$.transfers[?(@.direction=='out')].price").value(org.hamcrest.Matchers.hasItem(5.0)));

		String official = """
				{
				  "competition": {
				    "source": "sofascore",
				    "externalId": "17-transfers",
				    "name": "Premier League Transfers",
				    "season": "2026/27",
				    "slug": "premier-league-transfers"
				  },
				  "team": { "name": "Transfer FC", "managerName": "Locksat" },
				  "rounds": [
				    {
				      "number": 1,
				      "name": "Round 1",
				      "transferPenalty": 0,
				      "transfers": [
				        {
				          "playerIn": { "externalId": "979128", "name": "Rayan Cherki", "position": "MID", "club": "Manchester City", "clubExternalId": "17" },
				          "playerOut": { "externalId": "827606", "name": "Rodri", "position": "MID", "club": "Manchester City", "clubExternalId": "17" },
				          "priceIn": 8.5,
				          "priceOut": 6.5
				        }
				      ]
				    }
				  ]
				}
				""";
		mockMvc.perform(post("/api/v1/ingest/transfers")
						.contentType(MediaType.APPLICATION_JSON)
						.content(official))
				.andExpect(status().isCreated());
		mockMvc.perform(get("/api/v1/competitions/" + competitionId + "/team").param("gameweek", "1"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.transfers.length()").value(2))
				.andExpect(jsonPath("$.transfers[0].direction").value("in"))
				.andExpect(jsonPath("$.transfers[0].name").value("Rayan Cherki"))
				.andExpect(jsonPath("$.transfers[0].price").value(8.5))
				.andExpect(jsonPath("$.transfers[1].direction").value("out"))
				.andExpect(jsonPath("$.transfers[1].name").value("Rodri"))
				.andExpect(jsonPath("$.transfers[1].price").value(6.5));
	}

	@Test
	void officialLaLigaTransfersCanBeUnpairedBuysAndSells() throws Exception {
		String snapshot = """
				{
				  "competition": {
				    "source": "laliga-fantasy",
				    "externalId": "oficial",
				    "name": "LaLiga Fantasy",
				    "season": "2026/27",
				    "slug": "laliga-fantasy-oficial"
				  },
				  "gameweek": { "number": 2, "name": "GW2", "status": "finished" },
				  "team": { "name": "Los Oficiales", "managerName": "Locksat" },
				  "picks": [
				    {
				      "player": { "externalId": "823944", "name": "Kylian Mbappé", "position": "FWD", "club": "Real Madrid", "clubExternalId": "2829" },
				      "role": "starter",
				      "captain": false,
				      "viceCaptain": false,
				      "points": 10,
				      "price": 20
				    },
				    {
				      "player": { "externalId": "pedri-barcelona", "name": "Pedri", "position": "MID", "club": "Barcelona" },
				      "role": "squad",
				      "captain": false,
				      "viceCaptain": false,
				      "points": 0,
				      "price": 12,
				      "injured": true
				    }
				  ],
				  "teamPoints": 64
				}
				""";
		String created = mockMvc.perform(post("/api/v1/ingest/snapshots")
						.contentType(MediaType.APPLICATION_JSON)
						.content(snapshot))
				.andExpect(status().isCreated())
				.andReturn()
				.getResponse()
				.getContentAsString();
		int competitionId = new com.fasterxml.jackson.databind.ObjectMapper().readTree(created).get("competitionId").asInt();

		String deals = """
				{
				  "competition": {
				    "source": "laliga-fantasy",
				    "externalId": "oficial",
				    "name": "LaLiga Fantasy",
				    "season": "2026/27",
				    "slug": "laliga-fantasy-oficial"
				  },
				  "team": { "name": "Los Oficiales", "managerName": "Locksat" },
				  "rounds": [
				    {
				      "number": 2,
				      "name": "GW2",
				      "transfers": [
				        {
				          "playerIn": { "externalId": "1399376", "name": "Lamine Yamal", "position": "FWD", "club": "Barcelona", "clubExternalId": "2817" },
				          "priceIn": 18.0,
				          "counterpart": "Market"
				        },
				        {
				          "playerOut": { "externalId": "joselu-real-madrid", "name": "Joselu", "position": "FWD", "club": "Real Madrid", "clubExternalId": "2829" },
				          "priceOut": 9.0,
				          "counterpart": "Otro Manager FC"
				        }
				      ]
				    }
				  ]
				}
				""";
		mockMvc.perform(post("/api/v1/ingest/transfers")
						.contentType(MediaType.APPLICATION_JSON)
						.content(deals))
				.andExpect(status().isCreated());
		mockMvc.perform(get("/api/v1/competitions/" + competitionId + "/team").param("gameweek", "2"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.picks[?(@.role=='squad')].name").value(org.hamcrest.Matchers.hasItem("Pedri")))
				.andExpect(jsonPath("$.picks[?(@.name=='Pedri')].injured").value(org.hamcrest.Matchers.hasItem(true)))
				.andExpect(jsonPath("$.transfers.length()").value(2))
				.andExpect(jsonPath("$.transfers[?(@.direction=='in')].name").value(org.hamcrest.Matchers.hasItem("Lamine Yamal")))
				.andExpect(jsonPath("$.transfers[?(@.direction=='in')].counterpart").value(org.hamcrest.Matchers.hasItem("Market")))
				.andExpect(jsonPath("$.transfers[?(@.direction=='in')].channel").value(org.hamcrest.Matchers.hasItem("market")))
				.andExpect(jsonPath("$.transfers[?(@.direction=='out')].name").value(org.hamcrest.Matchers.hasItem("Joselu")))
				.andExpect(jsonPath("$.transfers[?(@.direction=='out')].counterpart").value(org.hamcrest.Matchers.hasItem("Otro Manager FC")))
				.andExpect(jsonPath("$.transfers[?(@.direction=='out')].channel").value(org.hamcrest.Matchers.hasItem("release-clause")))
				.andExpect(jsonPath("$.transferMarket.week.soldToMarket.count").value(0))
				.andExpect(jsonPath("$.transferMarket.week.soldReleaseClause.count").value(1))
				.andExpect(jsonPath("$.transferMarket.week.soldReleaseClause.total").value(9.0))
				.andExpect(jsonPath("$.transferMarket.week.boughtFromMarket.count").value(1))
				.andExpect(jsonPath("$.transferMarket.week.boughtFromMarket.total").value(18.0))
				.andExpect(jsonPath("$.transferMarket.week.boughtReleaseClause.count").value(0))
				.andExpect(jsonPath("$.transferMarket.week.soldTo[0].name").value("Otro Manager FC"))
				.andExpect(jsonPath("$.transferMarket.week.soldTo[0].total").value(9.0));
	}

	@Test
	void officialFplUsesPremierLeagueBrandingAndClubBadges() throws Exception {
		String snapshot = """
				{
				  "competition": {
				    "source": "fpl",
				    "externalId": "4795659",
				    "name": "Premier League Fantasy",
				    "season": "2026/27",
				    "slug": "premier-league-fantasy"
				  },
				  "gameweek": { "number": 1, "name": "Gameweek 1", "status": "finished" },
				  "team": { "name": "The Inbetweeners FC", "managerName": "Nicky Jones" },
				  "picks": [
				    {
				      "player": { "externalId": "975079", "name": "João Pedro", "position": "FWD", "club": "Chelsea", "clubExternalId": "8" },
				      "role": "starter",
				      "captain": true,
				      "viceCaptain": false,
				      "points": 11
				    }
				  ],
				  "teamPoints": 65,
				  "tripleCaptain": false
				}
				""";
		String created = mockMvc.perform(post("/api/v1/ingest/snapshots")
						.contentType(MediaType.APPLICATION_JSON)
						.content(snapshot))
				.andExpect(status().isCreated())
				.andReturn()
				.getResponse()
				.getContentAsString();
		int competitionId = new com.fasterxml.jackson.databind.ObjectMapper().readTree(created).get("competitionId").asInt();
		mockMvc.perform(get("/api/v1/competitions/" + competitionId + "/gameweeks/1"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.competition.name").value("Premier League Fantasy"))
				.andExpect(jsonPath("$.competition.primaryColor").value("#3c1c5a"))
				.andExpect(jsonPath("$.competition.logoUrl")
						.value("https://img.sofascore.com/api/v1/unique-tournament/17/image"))
				.andExpect(jsonPath("$.teamPoints").value(65.0))
				.andExpect(jsonPath("$.picks[0].points").value(22.0))
				.andExpect(jsonPath("$.picks[0].playerPortraitUrl")
						.value("https://img.sofascore.com/api/v1/player/975079/image"))
				.andExpect(jsonPath("$.picks[0].clubCrestUrl")
						.value("https://resources.premierleague.com/premierleague/badges/70/t8.png"));
	}

	@Test
	void officialWslUsesSofaScoreBrandingAndCrests() throws Exception {
		String snapshot = """
				{
				  "competition": {
				    "source": "wsl",
				    "externalId": "5b182499-9aa0-4e9b-8557-b4d37a4fd1eb",
				    "name": "WSL Fantasy",
				    "season": "2026/27",
				    "slug": "wsl-fantasy"
				  },
				  "gameweek": { "number": 1, "name": "Gameweek 1", "status": "finished" },
				  "team": { "name": "The Inbetweeners FC", "managerName": "Jack Sparrownx" },
				  "picks": [
				    {
				      "player": { "externalId": "222", "name": "Alexia Putellas", "position": "MID", "club": "London City Lionesses", "clubExternalId": "9002" },
				      "role": "starter",
				      "captain": true,
				      "viceCaptain": false,
				      "points": 2
				    }
				  ],
				  "teamPoints": 4,
				  "tripleCaptain": false
				}
				""";
		String created = mockMvc.perform(post("/api/v1/ingest/snapshots")
						.contentType(MediaType.APPLICATION_JSON)
						.content(snapshot))
				.andExpect(status().isCreated())
				.andReturn()
				.getResponse()
				.getContentAsString();
		int competitionId = new com.fasterxml.jackson.databind.ObjectMapper().readTree(created).get("competitionId").asInt();
		mockMvc.perform(get("/api/v1/competitions/" + competitionId + "/gameweeks/1"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.competition.name").value("WSL Fantasy"))
				.andExpect(jsonPath("$.competition.primaryColor").value("#06121e"))
				.andExpect(jsonPath("$.competition.secondaryColor").value("#00c2cb"))
				.andExpect(jsonPath("$.competition.logoUrl")
						.value("https://img.sofascore.com/api/v1/unique-tournament/1044/image"))
				.andExpect(jsonPath("$.teamPoints").value(4.0))
				.andExpect(jsonPath("$.picks[0].points").value(4.0))
				.andExpect(jsonPath("$.picks[0].playerPortraitUrl")
						.value("https://img.sofascore.com/api/v1/player/222/image"))
				.andExpect(jsonPath("$.picks[0].clubCrestUrl")
						.value("https://img.sofascore.com/api/v1/team/9002/image"));
	}

	private void ingest(String classpath) throws Exception {
		String body = new String(new ClassPathResource(classpath).getInputStream().readAllBytes(), StandardCharsets.UTF_8);
		mockMvc.perform(post("/api/v1/ingest/snapshots")
						.contentType(MediaType.APPLICATION_JSON)
						.content(body))
				.andExpect(status().isCreated());
	}
}
