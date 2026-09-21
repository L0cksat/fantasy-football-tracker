export interface Competition {
  id: number;
  source: string;
  externalId: string;
  name: string;
  season: string;
  slug: string;
  teamName: string | null;
  gameweeks: number[];
  logoUrl: string | null;
  logoDarkUrl: string | null;
  flagUrl: string | null;
  countryName: string | null;
  primaryColor: string | null;
  secondaryColor: string | null;
}

export interface HomePage {
  defaultCompetitionId: number | null;
  defaultCompetitionSlug: string;
  leagueBrands: LeagueBrand[];
  playersOfTheWeek: PlayerOfTheWeek[];
  latestWeekStandings: LeagueStanding[];
  europeTotalStandings: LeagueStanding[];
  americasTotalStandings: LeagueStanding[];
}

export interface LeagueBrand {
  brandKey: string;
  name: string;
  logoUrl: string | null;
  logoDarkUrl: string | null;
  primaryColor: string | null;
  secondaryColor: string | null;
}

export interface LeagueStanding {
  rank: number;
  competitionId: number;
  competitionName: string;
  competitionSlug: string;
  logoUrl: string | null;
  primaryColor: string | null;
  secondaryColor: string | null;
  gameweek: number | null;
  gameweekName: string | null;
  points: number;
}

export interface PlayerOfTheWeek {
  competitionId: number;
  competitionName: string;
  competitionSlug: string;
  logoUrl: string | null;
  primaryColor: string | null;
  secondaryColor: string | null;
  gameweek: number;
  gameweekName: string;
  playerId: number;
  externalId: string;
  name: string;
  shirtNumber: number | null;
  position: string | null;
  club: string | null;
  playerPortraitUrl: string | null;
  clubCrestUrl: string | null;
  points: number;
}

export interface TeamView {
  competition: {
    id: number;
    name: string;
    season: string;
    slug: string;
    logoUrl: string | null;
    logoDarkUrl: string | null;
    flagUrl: string | null;
    countryName: string | null;
    primaryColor: string | null;
    secondaryColor: string | null;
  };
  team: { id: number; name: string; managerName: string | null };
  gameweek: {
    number: number;
    name: string;
    status: string;
    startsAt: string | null;
    endsAt: string | null;
  };
  teamPoints: number;
  tripleCaptain: boolean;
  transferPenalty: number;
  picks: PickView[];
  transfers: TransferView[];
  transferMarket: TransferMarketSummary | null;
  longestServingPlayer: LongestServingPlayer | null;
}

export interface LongestServingPlayer {
  playerId: number;
  externalId: string;
  name: string;
  playerPortraitUrl: string | null;
  position: string | null;
  club: string | null;
  clubCrestUrl: string | null;
  shirtNumber: number | null;
  gameweeksStarted: number;
  totalPoints: number;
}

export interface TransferMarketSummary {
  week: TransferMarketScope;
  season: TransferMarketScope;
  mostExpensivePurchase: TransferHighlight | null;
  highestSale: TransferHighlight | null;
}

export interface TransferHighlight {
  playerId: number;
  externalId: string;
  name: string;
  playerPortraitUrl: string | null;
  position: string | null;
  club: string | null;
  clubCrestUrl: string | null;
  shirtNumber: number | null;
  price: number | null;
  counterpart: string | null;
  channel: 'market' | 'release-clause' | null;
  gameweekNumber: number | null;
  gameweekName: string | null;
}

export interface TransferMarketScope {
  soldToMarket: DealGroup;
  soldReleaseClause: DealGroup;
  boughtFromMarket: DealGroup;
  boughtReleaseClause: DealGroup;
  soldTo: CounterpartGroup[];
  boughtFrom: CounterpartGroup[];
}

export interface DealGroup {
  count: number;
  total: number;
}

export interface CounterpartGroup {
  name: string;
  count: number;
  total: number;
}

export interface TransferView {
  direction: 'in' | 'out';
  playerId: number;
  externalId: string;
  name: string;
  playerPortraitUrl: string | null;
  position: string | null;
  club: string | null;
  clubCrestUrl: string | null;
  price: number | null;
  counterpart: string | null;
  channel: 'market' | 'release-clause' | null;
}

export interface PickView {
  playerId: number;
  externalId: string;
  name: string;
  playerPortraitUrl: string | null;
  position: string | null;
  club: string | null;
  clubCrestUrl: string | null;
  shirtNumber: number | null;
  role: string;
  captain: boolean;
  viceCaptain: boolean;
  captainMultiplier: number;
  basePoints: number;
  points: number;
  rating: number | null;
  breakdown: string | null;
  injured: boolean;
  suspended: boolean;
}

export interface CompareView {
  fromGameweek: number;
  toGameweek: number;
  teamFromPoints: number;
  teamToPoints: number;
  teamDelta: number;
  players: PlayerDelta[];
}

export interface PlayerDelta {
  playerId: number;
  name: string;
  playerPortraitUrl: string | null;
  position: string | null;
  club: string | null;
  fromRole: string | null;
  toRole: string | null;
  fromPoints: number;
  toPoints: number;
  delta: number;
}

export interface TotalsView {
  competitionId: number;
  teamName: string;
  totalPoints: number;
  gameweeks: { number: number; name: string; status?: string | null; points: number }[];
}
